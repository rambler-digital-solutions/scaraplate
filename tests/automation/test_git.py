import contextlib
import json
from pathlib import Path

import pytest

from scaraplate.automation.base import automatic_rollup
from scaraplate.automation.git import (
    GitCloneProjectVCS,
    GitCloneTemplateVCS,
    strip_credentials_from_git_remote,
)


@contextlib.contextmanager
def git_unbare_repo(git_path: Path, call_git):
    call_git("git config --bool core.bare false", cwd=git_path)
    try:
        yield
    finally:
        call_git("git config --bool core.bare true", cwd=git_path)


def convert_bare_to_monorepo(dest: str, git_path: Path, call_git):
    with git_unbare_repo(git_path, call_git):
        dest_path = git_path / dest
        dest_path.mkdir()

        for child in git_path.iterdir():
            if child.name in (".git", dest):
                continue
            child.rename(dest_path / child.name)

        call_git("git add --all .", cwd=git_path)
        call_git('git commit -m "convert to monorepo"', cwd=git_path)
        call_git("git branch -f master2 master", cwd=git_path)


@pytest.mark.parametrize(
    "target_branch, clone_ref",
    [
        ("updates", None),
        ("updates", "master2"),
        ("updates", "master"),
        ("master", None),
        # master-master2 is excluded, because cloning a non-default branch and
        # committing the changes back to default is ridiculous
        ("master", "master"),
    ],
)
@pytest.mark.parametrize("monorepo_inner_path", ["inner", None])
def test_automatic_rollup(
    template_bare_git_repo: Path,
    project_bare_git_repo: Path,
    target_branch,
    clone_ref,
    monorepo_inner_path,
    call_git,
):
    if monorepo_inner_path is not None:
        convert_bare_to_monorepo(monorepo_inner_path, template_bare_git_repo, call_git)
        convert_bare_to_monorepo(monorepo_inner_path, project_bare_git_repo, call_git)

    assert "master" == call_git(
        "git rev-parse --abbrev-ref HEAD", cwd=project_bare_git_repo
    )
    master_commit_hash = call_git(
        "git rev-parse --verify master", cwd=project_bare_git_repo
    )
    template_commit_hash = call_git(
        f"git rev-parse --verify {clone_ref or 'master'}", cwd=template_bare_git_repo
    )

    automatic_rollup(
        template_vcs_ctx=GitCloneTemplateVCS.clone(
            clone_url=str(template_bare_git_repo),  # a clonable remote URL
            clone_ref=clone_ref,
            monorepo_inner_path=monorepo_inner_path,
        ),
        project_vcs_ctx=GitCloneProjectVCS.clone(
            clone_url=str(project_bare_git_repo),  # a clonable remote URL
            clone_ref=clone_ref,
            monorepo_inner_path=monorepo_inner_path,
            changes_branch=target_branch,
            commit_author="pytest <tests@none>",
        ),
        extra_context={"key1": "value1", "key2": "value2"},
    )

    target_branch_commit_hash = call_git(
        f"git rev-parse --verify {target_branch}", cwd=project_bare_git_repo
    )
    if target_branch == "master":
        # Ensure that master branch has advanced
        assert master_commit_hash != target_branch_commit_hash

    commit_message = call_git(
        f'git log --pretty=format:"%B" -n 1 {target_branch}', cwd=project_bare_git_repo
    )
    assert (clone_ref or "master") in commit_message  # template clone ref
    assert template_commit_hash in commit_message

    # Apply again (this time we expect no changes)
    automatic_rollup(
        template_vcs_ctx=GitCloneTemplateVCS.clone(
            clone_url=str(template_bare_git_repo),  # a clonable remote URL
            clone_ref=clone_ref,
            monorepo_inner_path=monorepo_inner_path,
        ),
        project_vcs_ctx=GitCloneProjectVCS.clone(
            clone_url=str(project_bare_git_repo),  # a clonable remote URL
            clone_ref=clone_ref,
            monorepo_inner_path=monorepo_inner_path,
            changes_branch=target_branch,
            commit_author="pytest <tests@none>",
        ),
        extra_context={"key1": "value1", "key2": "value2"},
    )

    target_branch_commit_hash_2 = call_git(
        f"git rev-parse --verify {target_branch}", cwd=project_bare_git_repo
    )
    assert target_branch_commit_hash == target_branch_commit_hash_2


def test_automatic_rollup_with_existing_target_branch(
    template_bare_git_repo: Path, project_bare_git_repo: Path, call_git
):
    target_branch = "update"

    assert "master" == call_git(
        "git rev-parse --abbrev-ref HEAD", cwd=project_bare_git_repo
    )
    master_commit_hash = call_git(
        "git rev-parse --verify master", cwd=project_bare_git_repo
    )

    # Create `update` branch with one version
    automatic_rollup(
        template_vcs_ctx=GitCloneTemplateVCS.clone(
            clone_url=str(template_bare_git_repo)  # a clonable remote URL
        ),
        project_vcs_ctx=GitCloneProjectVCS.clone(
            clone_url=str(project_bare_git_repo),  # a clonable remote URL
            changes_branch=target_branch,
            commit_author="pytest <tests@none>",
        ),
        extra_context={"key1": "first1", "key2": "first2"},
    )

    target_branch_commit_hash = call_git(
        f"git rev-parse --verify {target_branch}", cwd=project_bare_git_repo
    )

    # Apply again (but another version of template -- note the changed
    # extra_context
    automatic_rollup(
        template_vcs_ctx=GitCloneTemplateVCS.clone(
            clone_url=str(template_bare_git_repo)  # a clonable remote URL
        ),
        project_vcs_ctx=GitCloneProjectVCS.clone(
            clone_url=str(project_bare_git_repo),  # a clonable remote URL
            changes_branch=target_branch,
            commit_author="pytest <tests@none>",
        ),
        extra_context={"key1": "second1", "key2": "second2"},
    )

    master_commit_hash_2 = call_git(
        "git rev-parse --verify master", cwd=project_bare_git_repo
    )
    target_branch_commit_hash_2 = call_git(
        f"git rev-parse --verify {target_branch}", cwd=project_bare_git_repo
    )
    # The first push should be replaced with the second one:
    assert target_branch_commit_hash != target_branch_commit_hash_2
    # master should not be changed:
    assert master_commit_hash == master_commit_hash_2


@pytest.mark.parametrize("monorepo_inner_path", ["inner", None])
def test_automatic_rollup_preserves_template_dirname(
    template_bare_git_repo: Path,
    project_bare_git_repo: Path,
    monorepo_inner_path,
    call_git,
):
    target_branch = "update"

    if monorepo_inner_path is not None:
        convert_bare_to_monorepo(monorepo_inner_path, template_bare_git_repo, call_git)

    automatic_rollup(
        template_vcs_ctx=GitCloneTemplateVCS.clone(
            clone_url=str(template_bare_git_repo),  # a clonable remote URL
            monorepo_inner_path=monorepo_inner_path,
        ),
        project_vcs_ctx=GitCloneProjectVCS.clone(
            clone_url=str(project_bare_git_repo),  # a clonable remote URL
            changes_branch=target_branch,
            commit_author="pytest <tests@none>",
        ),
        extra_context={"key1": "value1", "key2": "value2"},
    )

    cookiecutter_context_text = call_git(
        f"git show {target_branch}:sense_vars", cwd=project_bare_git_repo
    )

    assert json.loads(cookiecutter_context_text) == {
        "_template": monorepo_inner_path if monorepo_inner_path else "remote_template",
        "project_dest": "remote_project",
        "key1": "value1",
        "key2": "value2",
    }


@pytest.mark.parametrize(
    "remote_url, expected_url",
    [
        (
            "https://oauth2:xxxtokenxxx@mygitlab.com/myorg/myproj.git",
            "https://mygitlab.com/myorg/myproj.git",
        ),
        (
            "https://mygitlab.com/myorg/myproj.git",
            "https://mygitlab.com/myorg/myproj.git",
        ),
        # I suppose ssh urls cannot contain a password?
        ("git@mygitlab.com:myorg/myproj.git", "git@mygitlab.com:myorg/myproj.git"),
        ("/var/myrepos/mybare", "/var/myrepos/mybare"),
    ],
)
def test_strip_credentials_from_git_remote(remote_url, expected_url):
    assert expected_url == strip_credentials_from_git_remote(remote_url)
