import pytest

from scaraplate.gitremotes import BitBucket, GitHub, GitLab, make_git_remote


@pytest.mark.parametrize(
    "remote, expected_remote",
    [
        ("git@gitlab.com:pycqa/flake8.git", GitLab),
        ("https://gitlab.com/pycqa/flake8.git", GitLab),
        ("https://gitlab.example.org/pycqa/flake8.git", GitLab),
        ("git@github.com:geopy/geopy.git", GitHub),
        ("https://github.com/geopy/geopy.git", GitHub),
        ("https://github.example.org/geopy/geopy.git", GitHub),
        ("https://bitbucket.org/someuser/someproject.git", BitBucket),
        ("https://git.example.org/pycqa/flake8.git", None),
    ],
)
def test_make_git_remote_detection(remote, expected_remote):
    if expected_remote is None:
        with pytest.raises(ValueError):
            make_git_remote(remote)
    else:
        assert expected_remote is type(make_git_remote(remote))  # noqa


@pytest.mark.parametrize(
    "remote, git_remote_type, expected_remote",
    [("https://git.example.org/pycqa/flake8.git", GitLab, GitLab)],
)
def test_make_git_remote_custom(remote, git_remote_type, expected_remote):
    assert expected_remote is type(  # noqa
        make_git_remote(remote, git_remote_type=git_remote_type)
    )


@pytest.mark.parametrize(
    "remote, expected",
    [
        ("git@gitlab.com:pycqa/flake8.git", "https://gitlab.com/pycqa/flake8"),
        ("https://gitlab.com/pycqa/flake8.git", "https://gitlab.com/pycqa/flake8"),
        (
            "git@gitlab.example.org:pycqa/flake8.git",
            "https://gitlab.example.org/pycqa/flake8",
        ),
        (
            "https://gitlab.example.org/pycqa/flake8.git",
            "https://gitlab.example.org/pycqa/flake8",
        ),
    ],
)
def test_gitlab_url_from_remote(remote, expected):
    assert expected == GitLab(remote).project_url()


@pytest.mark.parametrize(
    "remote, commit_hash, expected_url",
    [
        (
            "https://gitlab.com/pycqa/flake8.git",
            "1111111111111111111111111111111111111111",
            "https://gitlab.com/pycqa/flake8/commit/"
            "1111111111111111111111111111111111111111",
        )
    ],
)
def test_gitlab_commit_url(remote, commit_hash, expected_url):
    assert expected_url == GitLab(remote).commit_url(commit_hash)


@pytest.mark.parametrize(
    "remote, expected",
    [
        ("git@github.com:geopy/geopy.git", "https://github.com/geopy/geopy"),
        ("https://github.com/geopy/geopy.git", "https://github.com/geopy/geopy"),
        (
            "git@github.example.org:geopy/geopy.git",
            "https://github.example.org/geopy/geopy",
        ),
        (
            "https://github.example.org/geopy/geopy.git",
            "https://github.example.org/geopy/geopy",
        ),
    ],
)
def test_github_url_from_remote(remote, expected):
    assert expected == GitHub(remote).project_url()


@pytest.mark.parametrize(
    "remote, commit_hash, expected_url",
    [
        (
            "https://github.com/geopy/geopy.git",
            "1111111111111111111111111111111111111111",
            "https://github.com/geopy/geopy/commit/"
            "1111111111111111111111111111111111111111",
        )
    ],
)
def test_github_commit_url(remote, commit_hash, expected_url):
    assert expected_url == GitHub(remote).commit_url(commit_hash)


@pytest.mark.parametrize(
    "remote, expected",
    [
        (
            "git@bitbucket.org:someuser/someproject.git",
            "https://bitbucket.org/someuser/someproject",
        ),
        (
            "https://bitbucket.org/someuser/someproject.git",
            "https://bitbucket.org/someuser/someproject",
        ),
    ],
)
def test_bitbucket_url_from_remote(remote, expected):
    assert expected == BitBucket(remote).project_url()


@pytest.mark.parametrize(
    "remote, commit_hash, expected_url",
    [
        (
            "https://bitbucket.org/someuser/someproject.git",
            "1111111111111111111111111111111111111111",
            "https://bitbucket.org/someuser/someproject/commits/"
            "1111111111111111111111111111111111111111",
        )
    ],
)
def test_bitbucket_commit_url(remote, commit_hash, expected_url):
    assert expected_url == BitBucket(remote).commit_url(commit_hash)
