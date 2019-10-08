import json
from unittest.mock import call, patch, sentinel

import pytest

import scaraplate.automation.gitlab
from scaraplate.automation.gitlab import (
    GitLabCloneTemplateVCS,
    GitLabMRProjectVCS,
    gitlab_available,
    gitlab_clone_url,
    gitlab_project_url,
)
from scaraplate.template import TemplateMeta


@pytest.mark.parametrize(
    "project_url, private_token, expected_url",
    [
        (
            "https://mygitlab.com/myorg/myproj.git",
            "xxxtokenxxx",
            "https://oauth2:xxxtokenxxx@mygitlab.com/myorg/myproj.git",
        ),
        (
            "https://mygitlab.com/myorg/myproj",
            "xxxtokenxxx",
            "https://oauth2:xxxtokenxxx@mygitlab.com/myorg/myproj.git",
        ),
        (
            "https://mygitlab.com/myorg/myproj",
            None,
            "https://mygitlab.com/myorg/myproj.git",
        ),
    ],
)
def test_gitlab_clone_url(project_url, private_token, expected_url):
    assert expected_url == gitlab_clone_url(project_url, private_token)


@pytest.mark.parametrize(
    "gitlab_url, full_project_name, expected_url",
    [
        ("https://mygitlab.com", "myorg/myproj", "https://mygitlab.com/myorg/myproj"),
        (
            "https://mygitlab.com/",
            "myorg/myproj.git",
            "https://mygitlab.com/myorg/myproj.git",
        ),
    ],
)
def test_gitlab_project_url(gitlab_url, full_project_name, expected_url):
    assert expected_url == gitlab_project_url(gitlab_url, full_project_name)


def test_gitlab_clone_template(template_bare_git_repo, call_git):
    with patch.object(
        scaraplate.automation.gitlab,
        "gitlab_clone_url",
        return_value=str(template_bare_git_repo),
    ) as mock_gitlab_clone_url:
        with GitLabCloneTemplateVCS.clone(
            project_url=sentinel.project_url, private_token=sentinel.private_token
        ) as template_vcs:
            # Ensure this is a valid git repo:
            call_git("git status", cwd=template_vcs.dest_path)

            assert template_vcs.template_meta.head_ref == "master"
        assert mock_gitlab_clone_url.call_count == 1
        assert mock_gitlab_clone_url.call_args == call(
            sentinel.project_url, sentinel.private_token
        )


@pytest.mark.skipif(
    gitlab_available, reason="gitlab should not be installed for this test"
)
def test_gitlab_mr_project_raises_without_gitlab():
    with pytest.raises(ImportError):
        with GitLabMRProjectVCS.clone(
            gitlab_url="http://a",
            full_project_name="a/aa",
            private_token="zzz",
            changes_branch="update",
        ):
            raise AssertionError("should not be executed")


@pytest.mark.skipif(
    not gitlab_available, reason="gitlab should be installed for this test"
)
@pytest.mark.parametrize(
    "mr_exists, changes_branch",
    [
        (False, "update"),
        (True, "update"),
        (None, "master"),  # MRs cannot be created from default branch
    ],
)
def test_gitlab_mr_project(
    project_bare_git_repo, call_git, http_server, mr_exists, changes_branch
):
    requests = iter(
        [
            (
                "GET",
                "/api/v4/user",
                {
                    # https://docs.gitlab.com/ee/api/users.html#list-current-user-for-normal-users
                    "name": "test user",
                    "email": "test@notemail",
                },
                None,
            ),
            (
                "GET",
                "/api/v4/projects/a%2Faa",
                {
                    # https://docs.gitlab.com/ee/api/projects.html#get-single-project
                    "id": 42,
                    "name": "test project",
                    "default_branch": "master",
                },
                None,
            ),
        ]
        + (
            []
            if mr_exists is None
            else [
                (
                    "GET",
                    "/api/v4/projects/42/merge_requests"
                    "?state=opened&source_branch=update&target_branch=master",
                    [] if not mr_exists else [{"id": 98, "iid": 98}],
                    None,
                )
            ]
        )
        + (
            []
            if mr_exists or mr_exists is None
            else [
                (
                    "POST",  # type: ignore
                    "/api/v4/projects/42/merge_requests",
                    {"id": 99, "iid": 99},
                    lambda body: mr_body_checker(body),
                )
            ]
        )
    )

    def mr_body_checker(body):
        data = json.loads(body.decode())
        assert "1111111111111111111111111111111111111111" in data["description"]

    @http_server.set_request_handler
    def request_handler(method, path, headers, body):
        assert headers["PRIVATE-TOKEN"] == "zzz"
        try:
            exp_method, exp_path, response, body_checker = next(requests)
        except StopIteration:  # pragma: no cover
            raise AssertionError(f"Received unexpected request {method} {path}")
        assert method == exp_method
        assert path == exp_path
        if body_checker is not None:
            body_checker(body)
        return 200, {"Content-type": "application/json"}, json.dumps(response).encode()

    with patch.object(
        scaraplate.automation.gitlab,
        "gitlab_clone_url",
        return_value=str(project_bare_git_repo),
    ) as mock_gitlab_clone_url:
        with GitLabMRProjectVCS.clone(
            gitlab_url=http_server.get_url(),
            full_project_name="a/aa",
            private_token="zzz",
            changes_branch=changes_branch,
        ) as project_vcs:
            # Ensure this is a valid git repo:
            call_git("git status", cwd=project_vcs.dest_path)

            assert not project_vcs.is_dirty()

            (project_vcs.dest_path / "hi").write_text("change!")
            project_vcs.commit_changes(
                TemplateMeta(
                    git_project_url="https://testdomain/t/tt",
                    commit_hash="1111111111111111111111111111111111111111",
                    commit_url=(
                        "https://testdomain/t/tt"
                        "/commit/1111111111111111111111111111111111111111"
                    ),
                    is_git_dirty=False,
                    head_ref="master",
                )
            )

            commit_message = call_git(
                f'git log --pretty=format:"%B" -n 1 {changes_branch}',
                cwd=project_bare_git_repo,
            )
            assert "1111111111111111111111111111111111111111" in commit_message
            assert "Scheduled" in commit_message

            commit_author = call_git(
                f'git log --pretty=format:"%aN <%aE>" -n 1 {changes_branch}',
                cwd=project_bare_git_repo,
            )
            assert commit_author == "test user <test@notemail>"

            assert "change!" == call_git(
                f"git show {changes_branch}:hi", cwd=project_bare_git_repo
            )

        assert mock_gitlab_clone_url.call_count == 1
        assert mock_gitlab_clone_url.call_args == call(
            f"{http_server.get_url()}/a/aa", "zzz"
        )

        # ensure that all expected queries have been executed:
        assert next(requests, ...) is ...
