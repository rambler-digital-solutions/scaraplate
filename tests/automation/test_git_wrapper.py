from pathlib import Path

import pytest

from scaraplate.automation.git import Git


@pytest.fixture
def git_repo(init_git_and_commit, tempdir_path):
    repo_path = tempdir_path / "repo"
    repo_path.mkdir()
    (repo_path / "readme").write_text("hi")
    init_git_and_commit(repo_path, with_remote=False)

    return repo_path


@pytest.mark.parametrize(
    "remote, ref, expected_ref", [("origin", "my-branch", "origin/my-branch")]
)
def test_git_remote_ref(remote, ref, expected_ref):
    git = Git(cwd=Path("."), remote=remote)
    assert expected_ref == git.remote_ref(ref)


def test_git_commit(git_repo, call_git):
    git = Git(git_repo)
    assert not git.is_dirty()

    (git_repo / "myfile").write_text("my precious")
    assert git.is_dirty()

    message = "my\nmultiline\nmessage"
    author = "John Doe <whitehouse@gov>"
    git.commit_all(message, author=author)
    assert not git.is_dirty()

    assert message == call_git("git log -1 --pretty=%B", cwd=git_repo)
    assert author == call_git("git log -1 --pretty='%an <%ae>'", cwd=git_repo)


def test_git_is_existing_ref(git_repo):
    git = Git(git_repo)
    assert git.is_existing_ref("master")
    assert not git.is_existing_ref("origin/master")


def test_git_are_one_commit_diffs_equal(git_repo, call_git):
    git = Git(git_repo)

    with pytest.raises(RuntimeError):
        # These refs don't exist yet
        git.are_one_commit_diffs_equal("t1", "t2")

    # Create branch t1
    git.checkout_branch("t1")
    (git_repo / "common").write_text("same")
    git.commit_all("m1")

    # Move master 1 commit ahead
    call_git("git checkout master", cwd=git_repo)
    (git_repo / "some_file").write_text("i'ma sta")
    call_git("git add .", cwd=git_repo)
    call_git("git commit -m next", cwd=git_repo)

    # Create branch t2
    git.checkout_branch("t2")
    (git_repo / "common").write_text("same")
    git.commit_all("m2")

    #      /-()  << t1 (/common == "same")
    #     /
    # -> () -> () -> ()  << t2 (/common == "same")
    #           \
    #            \  << master (/some_file == "i'ma sta")
    assert git.are_one_commit_diffs_equal("t1", "t2")
    assert git.are_one_commit_diffs_equal("master", "master")
    assert not git.are_one_commit_diffs_equal("master", "t2")
