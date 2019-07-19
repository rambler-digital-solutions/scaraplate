import abc
import re
from typing import Optional, Type


def _dot_git_remote_to_https(remote_url: str) -> str:
    url = remote_url
    # `git@gitlab.com:<suffix>` -> `https://gitlab.com/<suffix>`
    url = re.sub(r"^[^@]*@([^:]+):", r"https://\1/", url)
    url = re.sub(r".git$", "", url)
    return url


def make_git_remote(
    remote: str, *, git_remote_type: Optional[Type["GitRemote"]] = None
) -> "GitRemote":
    if git_remote_type is not None:
        return git_remote_type(remote)

    if "gitlab" in remote.lower():
        return GitLab(remote)
    elif "github" in remote.lower():
        return GitHub(remote)
    elif "bitbucket" in remote.lower():
        return BitBucket(remote)
    else:
        raise ValueError(
            "Unable to automatically determine the GitRemote type. "
            "Please set a specific one in the `scaraplate.yaml` config "
            "using the `git_remote_type` option."
        )


class GitRemote(abc.ABC):
    def __init__(self, remote: str) -> None:
        self.remote = remote

    @abc.abstractmethod
    def project_url(self) -> str:
        pass

    @abc.abstractmethod
    def commit_url(self, commit_hash: str) -> str:
        pass


class GitLab(GitRemote):
    def project_url(self) -> str:
        return _dot_git_remote_to_https(self.remote)

    def commit_url(self, commit_hash: str) -> str:
        project_url = self.project_url()
        return f"{project_url.rstrip('/')}/commit/{commit_hash}"


class GitHub(GitRemote):
    def project_url(self) -> str:
        return _dot_git_remote_to_https(self.remote)

    def commit_url(self, commit_hash: str) -> str:
        project_url = self.project_url()
        return f"{project_url.rstrip('/')}/commit/{commit_hash}"


class BitBucket(GitRemote):
    def project_url(self) -> str:
        return _dot_git_remote_to_https(self.remote)

    def commit_url(self, commit_hash: str) -> str:
        project_url = self.project_url()
        return f"{project_url.rstrip('/')}/commits/{commit_hash}"
