"""Scaraplate assumes that the template dir is a git repo.

Strategies receive a :class:`scaraplate.template.TemplateMeta` instance
which contains URLs to the template's project and the HEAD git commit
on a git remote's web interface (such as GitHub). These URLs might be
rendered in the target files by the strategies.

Scaraplate has built-in support for some popular git remotes. The remote
is attempted to be detected automatically, but if that fails, it should
be specified manually.


Sample ``scaraplate.yaml`` excerpt:

::

    git_remote_type: scaraplate.gitremotes.GitHub

"""
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
    """Base class for a git remote implementation, which generates http
    URLs from a git remote (either ssh of http) and a commit hash.
    """

    def __init__(self, remote: str) -> None:
        """Init the git remote.

        :param remote: A git remote, either ssh or http(s).
        """
        self.remote = remote

    @abc.abstractmethod
    def project_url(self) -> str:
        """Return a project URL at the given git remote."""
        pass

    @abc.abstractmethod
    def commit_url(self, commit_hash: str) -> str:
        """Return a commit URL at the given git remote.

        :param commit_hash: Git commit hash.
        """
        pass


class GitLab(GitRemote):
    """GitLab git remote implementation."""

    def project_url(self) -> str:
        return _dot_git_remote_to_https(self.remote)

    def commit_url(self, commit_hash: str) -> str:
        project_url = self.project_url()
        return f"{project_url.rstrip('/')}/commit/{commit_hash}"


class GitHub(GitRemote):
    """GitHub git remote implementation."""

    def project_url(self) -> str:
        return _dot_git_remote_to_https(self.remote)

    def commit_url(self, commit_hash: str) -> str:
        project_url = self.project_url()
        return f"{project_url.rstrip('/')}/commit/{commit_hash}"


class BitBucket(GitRemote):
    """BitBucket git remote implementation."""

    def project_url(self) -> str:
        return _dot_git_remote_to_https(self.remote)

    def commit_url(self, commit_hash: str) -> str:
        project_url = self.project_url()
        return f"{project_url.rstrip('/')}/commits/{commit_hash}"
