import pytest

from scaraplate.template import _git_head_commit_hash, _git_remote_origin, _is_git_dirty


def test_git_head_commit_hash_valid(init_git_and_commit, tempdir_path):
    repo_path = tempdir_path / "repo"
    repo_path.mkdir()
    (repo_path / "myfile").write_text("hi")
    init_git_and_commit(repo_path)

    assert 40 == len(_git_head_commit_hash(repo_path))


def test_git_head_commit_hash_invalid(tempdir_path):
    # tempdir_path is not under a git repo.
    with pytest.raises(RuntimeError):
        _git_head_commit_hash(tempdir_path)


def test_git_is_dirty(init_git_and_commit, tempdir_path, call_git):
    repo_path = tempdir_path / "repo"
    repo_path.mkdir()
    (repo_path / "myfile").write_text("hi")
    init_git_and_commit(repo_path)

    assert not _is_git_dirty(repo_path)

    # Unstaged should be considered dirty
    (repo_path / "myfile2").write_text("hi")
    assert _is_git_dirty(repo_path)

    # Staged should be considered dirty as well
    call_git("git add myfile2", cwd=repo_path)
    assert _is_git_dirty(repo_path)


def test_git_remote_origin_valid(init_git_and_commit, tempdir_path):
    repo_path = tempdir_path / "repo"
    repo_path.mkdir()
    (repo_path / "myfile").write_text("hi")
    init_git_and_commit(repo_path)

    assert _git_remote_origin(repo_path).startswith("https://")


def test_git_remote_origin_invalid(init_git_and_commit, tempdir_path):
    repo_path = tempdir_path / "repo"
    repo_path.mkdir()
    (repo_path / "myfile").write_text("hi")
    init_git_and_commit(repo_path, with_remote=False)

    with pytest.raises(RuntimeError):
        _git_remote_origin(repo_path)
