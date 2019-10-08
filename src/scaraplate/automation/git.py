import contextlib
import datetime
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Iterator, List, Optional
from urllib.parse import urlparse, urlunparse

from pkg_resources import get_distribution

from scaraplate.automation.base import ProjectVCS, TemplateVCS
from scaraplate.config import get_scaraplate_yaml_options
from scaraplate.template import TemplateMeta, _call_git, get_template_meta_from_git


__all__ = ("GitCloneProjectVCS", "GitCloneTemplateVCS")

logger = logging.getLogger("scaraplate")


def scaraplate_version() -> str:
    return get_distribution("scaraplate").version


class GitCloneTemplateVCS(TemplateVCS):
    """XXX"""

    def __init__(self, template_path: Path, template_meta: TemplateMeta) -> None:
        self._template_path = template_path
        self._template_meta = template_meta

    @property
    def dest_path(self) -> Path:
        return self._template_path

    @property
    def template_meta(self) -> TemplateMeta:
        return self._template_meta

    @classmethod
    @contextlib.contextmanager
    def clone(
        cls,
        clone_url: str,
        *,
        clone_ref: Optional[str] = None,
        monorepo_inner_path: Optional[Path] = None,
    ) -> Iterator["GitCloneTemplateVCS"]:
        """XXX"""

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir_path = Path(tmpdir_name).resolve()
            template_path = tmpdir_path / "scaraplate_template"

            Git.clone(
                clone_url,
                target_path=template_path,
                ref=clone_ref,
                # We need to strip credentials from the clone_url,
                # because otherwise urls generated for TemplateMeta
                # would contain them, and we don't want that.
                strip_credentials_from_remote=True,
            )

            if monorepo_inner_path is not None:
                template_path = template_path / monorepo_inner_path

            scaraplate_yaml_options = get_scaraplate_yaml_options(template_path)
            template_meta = get_template_meta_from_git(
                template_path, git_remote_type=scaraplate_yaml_options.git_remote_type
            )
            if clone_ref is not None:
                assert clone_ref == template_meta.head_ref

            yield cls(template_path, template_meta)


class GitCloneProjectVCS(ProjectVCS):
    """XXX"""

    def __init__(
        self,
        project_path: Path,
        git: "Git",
        *,
        changes_branch: str,
        commit_author: str,
        commit_message_template: str,
    ) -> None:
        self._project_path = project_path
        self._git = git
        self.changes_branch = changes_branch
        self.commit_author = commit_author
        self.commit_message_template = commit_message_template
        self.update_time = datetime.datetime.now()

    @property
    def dest_path(self) -> Path:
        return self._project_path

    def is_dirty(self) -> bool:
        return self._git.is_dirty()

    def commit_changes(self, template_meta: TemplateMeta) -> None:
        assert self.is_dirty()

        remote_branch = self._git.remote_ref(self.changes_branch)

        # Create a definitely not existing local branch:
        local_branch = f"{self.changes_branch}{uuid.uuid4()}"
        self._git.checkout_branch(local_branch)

        self._git.commit_all(
            self.format_commit_message(template_meta=template_meta),
            author=self.commit_author,
        )

        if not self._git.is_existing_ref(remote_branch):
            self._git.push(self.changes_branch)
        else:
            # A branch with updates already exists in the remote.

            if self._git.is_same_commit(remote_branch, f"{local_branch}^1"):
                # The `changes_branch` is the same as the clone branch,
                # so essentially the created commit forms a linear history.
                # No need for any diffs here, we just need to push that.
                self._git.push(self.changes_branch)
            else:
                # The two branches have diverged, we need to compare them:
                changes: bool = not self._git.are_one_commit_diffs_equal(
                    local_branch, remote_branch
                )

                if changes:
                    # We could've used force push here, but instead we delete
                    # the branch first, because in GitLab it would also close
                    # the existing MR (if any), and we want that instead of
                    # silently updating the old MR.
                    self._git.push_branch_delete(self.changes_branch)
                    self._git.push(self.changes_branch)
                else:
                    logger.info(
                        "scaraplate did update the project, but there's "
                        "an already existing branch in remote which diff "
                        "is equal to the just produced changes"
                    )

        # Now we should ensure that a Pull Request exists for
        # the `self.changes_branch`, but this class is designed to be agnostic
        # from concrete git remotes, so it should be done in a child class.

    def format_commit_message(self, *, template_meta: TemplateMeta) -> str:
        return self.commit_message_template.format(
            # TODO retrieve path from self.clone_url and pass it here too?
            # (but careful: that clone_url might contain credentials).
            update_time=self.update_time,
            scaraplate_version=scaraplate_version(),
            template_meta=template_meta,
        )

    @classmethod
    @contextlib.contextmanager
    def clone(
        cls,
        clone_url: str,
        *,
        clone_ref: Optional[str] = None,
        monorepo_inner_path: Optional[Path] = None,
        changes_branch: str,
        commit_author: str,
        commit_message_template: str = (
            "Scheduled template update ({update_time:%Y-%m-%d})\n"
            "\n"
            "* scaraplate version: {scaraplate_version}\n"
            "* template commit: {template_meta.commit_url}\n"
            "* template ref: {template_meta.head_ref}\n"
        ),
    ) -> Iterator["GitCloneProjectVCS"]:
        """XXX"""

        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir_path = Path(tmpdir_name).resolve()
            project_path = tmpdir_path / "scaraplate_project"

            git = Git.clone(clone_url, target_path=project_path, ref=clone_ref)

            if monorepo_inner_path is not None:
                project_path = project_path / monorepo_inner_path

            yield cls(
                project_path,
                git,
                changes_branch=changes_branch,
                commit_author=commit_author,
                commit_message_template=commit_message_template,
            )


class Git:
    def __init__(self, cwd: Path, remote: str = "origin") -> None:
        self.cwd = cwd
        self.remote = remote

    def remote_ref(self, ref: str) -> str:
        return f"{self.remote}/{ref}"

    def checkout_branch(self, branch: str) -> None:
        self._git(["checkout", "-b", branch])

    def commit_all(self, commit_message: str, author: Optional[str] = None) -> None:
        self._git(["add", "--all"])
        extra: List[str] = []
        if author is not None:
            extra = ["--author", author]
        self._git(
            ["commit", "-m", commit_message, *extra],
            env={
                # git would fail if there's no `user.email` in the local
                # git config, even if `--author` is specified.
                "USERNAME": "scaraplate",
                "EMAIL": "scaraplate@localhost",
            },
        )

    def is_dirty(self) -> bool:
        return bool(self._git(["status", "--porcelain"]))

    def is_existing_ref(self, ref: str) -> bool:
        try:
            self._git(["rev-parse", "--verify", ref])
        except RuntimeError:
            return False
        else:
            return True

    def is_same_commit(self, ref1: str, ref2: str) -> bool:
        commit1 = self._git(["rev-parse", "--verify", ref1])
        commit2 = self._git(["rev-parse", "--verify", ref2])
        return commit1 == commit2

    def are_one_commit_diffs_equal(self, ref1: str, ref2: str) -> bool:
        diff1 = self._git(["diff", f"{ref1}^1..{ref1}"])
        diff2 = self._git(["diff", f"{ref2}^1..{ref2}"])
        return diff1 == diff2

    def push_branch_delete(self, branch: str) -> None:
        self._git(["push", "--delete", self.remote, branch])

    def push(self, ref: str) -> None:
        # https://stackoverflow.com/a/4183856
        self._git(["push", self.remote, f"HEAD:{ref}"])

    def _git(self, args: List[str], *, env: Optional[Dict[str, str]] = None) -> str:
        return _call_git(args, cwd=self.cwd, env=env)

    @classmethod
    def clone(
        cls,
        clone_url: str,
        *,
        target_path: Path,
        ref: str = None,
        strip_credentials_from_remote: bool = False,
    ) -> "Git":
        remote = "origin"
        clone_url_without_creds = strip_credentials_from_git_remote(clone_url)

        args = ["clone", clone_url, target_path.name]

        if ref is not None:
            # git-clone(1) explicitly mentions that both branches and tags
            # are allowed in the `--branch`.
            args.extend(["--branch", ref])

        _call_git(args, cwd=target_path.parent)

        if not target_path.is_dir():
            raise RuntimeError(
                f"Expected `git` to clone '{clone_url_without_creds}' to "
                f"'{target_path}', but it didn't"
            )

        if strip_credentials_from_remote:
            _call_git(
                ["remote", "set-url", remote, clone_url_without_creds], cwd=target_path
            )

        return cls(cwd=target_path, remote=remote)


def strip_credentials_from_git_remote(remote: str) -> str:
    parsed = urlparse(remote)
    if not parsed.scheme:
        # Not a URL (probably an SSH remote)
        return remote
    assert parsed.hostname is not None
    clean = parsed._replace(netloc=parsed.hostname)
    return urlunparse(clean)
