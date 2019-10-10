import contextlib
import logging
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse, urlunparse

from scaraplate.automation.base import ProjectVCS, TemplateVCS
from scaraplate.automation.git import (
    GitCloneProjectVCS,
    GitCloneTemplateVCS,
    scaraplate_version,
)
from scaraplate.template import TemplateMeta


try:
    import gitlab
except ImportError:
    gitlab_available = False
else:
    gitlab_available = True


logger = logging.getLogger("scaraplate")


def ensure_gitlab_is_installed():
    if not gitlab_available:
        raise ImportError(
            "python-gitlab must be installed in order to use GitLab integration. "
            'Install with `pip install "scaraplate[gitlab]"`.'
        )


def gitlab_clone_url(project_url: str, private_token: Optional[str]) -> str:
    parsed = urlparse(project_url)
    assert parsed.scheme

    if private_token:
        clean = parsed._replace(netloc=f"oauth2:{private_token}@{parsed.hostname}")
    else:
        clean = parsed
    if not clean.path.endswith(".git"):
        clean = clean._replace(path=f"{clean.path}.git")
    return urlunparse(clean)


def gitlab_project_url(gitlab_url: str, full_project_name: str) -> str:
    return urljoin(gitlab_url, full_project_name)


class GitLabCloneTemplateVCS(TemplateVCS):
    """A class which extends :class:`.GitCloneTemplateVCS` with
    GitLab-specific ``clone_url`` generation.
    """

    def __init__(self, git_clone: GitCloneTemplateVCS) -> None:
        self._git_clone = git_clone

    @property
    def dest_path(self) -> Path:
        return self._git_clone.dest_path

    @property
    def template_meta(self) -> TemplateMeta:
        return self._git_clone.template_meta

    @classmethod
    @contextlib.contextmanager
    def clone(
        cls,
        project_url: str,
        private_token: Optional[str] = None,
        *,
        clone_ref: Optional[str] = None,
        monorepo_inner_path: Optional[Path] = None,
    ) -> Iterator["GitLabCloneTemplateVCS"]:
        """Same as :meth:`.GitCloneTemplateVCS.clone` except that
        ``clone_url`` is replaced with ``project_url`` and ``private_token``.

        The ``private_token`` allows to clone private repos, which are
        visible only for an authenticated user.

        :param project_url: A URL to a GitLab project, e.g.
            ``https://gitlab.example.org/myorganization/myproject``.
        :param private_token: GitLab access token,
            see `<https://docs.gitlab.com/ce/api/#oauth2-tokens>`_.
        """

        with GitCloneTemplateVCS.clone(
            clone_url=gitlab_clone_url(project_url, private_token),
            clone_ref=clone_ref,
            monorepo_inner_path=monorepo_inner_path,
        ) as git_clone:
            yield cls(git_clone)


class GitLabMRProjectVCS(ProjectVCS):
    """A class which extends :class:`.GitCloneProjectVCS` with
    GitLab-specific ``clone_url`` generation and opens a GitLab Merge Request
    after ``git push``.
    """

    def __init__(
        self,
        git_clone: GitCloneProjectVCS,
        *,
        gitlab_project,
        mr_title_template: str,
        mr_description_markdown_template: str,
    ) -> None:
        self._git_clone = git_clone
        self._gitlab_project = gitlab_project
        self.mr_title_template = mr_title_template
        self.mr_description_markdown_template = mr_description_markdown_template

    @property
    def dest_path(self) -> Path:
        return self._git_clone.dest_path

    def is_dirty(self) -> bool:
        return self._git_clone.is_dirty()

    def commit_changes(self, template_meta: TemplateMeta) -> None:
        self._git_clone.commit_changes(template_meta)

        if self._git_clone.changes_branch == self._gitlab_project.default_branch:
            logger.info(
                "Skipping MR creation step as `changes_branch` and `default_branch` "
                "are the same, i.e. the changes are already in the target branch."
            )
        else:
            self.create_merge_request(
                title=self.format_merge_request_title(template_meta=template_meta),
                description=self.format_merge_request_description(
                    template_meta=template_meta
                ),
            )

    def format_merge_request_title(self, *, template_meta: TemplateMeta) -> str:
        return self.mr_title_template.format(
            update_time=self._git_clone.update_time, template_meta=template_meta
        )

    def format_merge_request_description(self, *, template_meta: TemplateMeta) -> str:
        # The returned string would be treated as markdown markup.
        return self.mr_description_markdown_template.format(
            update_time=self._git_clone.update_time,
            scaraplate_version=scaraplate_version(),
            template_meta=template_meta,
        )

    def create_merge_request(self, *, title: str, description: str) -> None:
        existing_mr = self.get_merge_request()
        if existing_mr is not None:
            logger.info(f"Skipping MR creation as it already exists: {existing_mr!r}")
            return

        self._gitlab_project.mergerequests.create(
            {
                "description": description,
                "should_remove_source_branch": True,
                "source_branch": self._git_clone.changes_branch,
                "target_branch": self._gitlab_project.default_branch,
                "title": title,
            }
        )

    def get_merge_request(self):
        merge_requests = self._gitlab_project.mergerequests.list(
            state="opened",
            source_branch=self._git_clone.changes_branch,
            target_branch=self._gitlab_project.default_branch,
        )

        if not merge_requests:
            return None

        assert len(merge_requests) == 1, merge_requests
        merge_request = merge_requests[0]
        return merge_request

    @classmethod
    @contextlib.contextmanager
    def clone(
        cls,
        gitlab_url: str,
        full_project_name: str,
        private_token: str,
        *,
        mr_title_template: str = "Scheduled template update ({update_time:%Y-%m-%d})",
        mr_description_markdown_template: str = (
            "* scaraplate version: `{scaraplate_version}`\n"
            "* template commit: {template_meta.commit_url}\n"
            "* template ref: {template_meta.head_ref}\n"
        ),
        commit_author: Optional[str] = None,
        **kwargs,
    ) -> Iterator["GitLabMRProjectVCS"]:
        """Same as :meth:`.GitCloneProjectVCS.clone` with the following
        exceptions:

        - ``clone_url`` is replaced with ``gitlab_url``, ``full_project_name``
          and ``private_token``.
        - A GitLab Merge Request (MR) is opened after a successful
          ``git push``.

        The ``private_token`` allows to clone private repos, which are
        visible only for an authenticated user.

        As in :meth:`.GitCloneProjectVCS.clone`, the ``changes_branch``
        might be the same as ``clone_ref``. In this case no MR will be
        opened.

        A MR will be created only if there're any changes produced
        by scaraplate rollup. If a ``changes_branch`` is already present
        in remote (i.e. there is a previous automatic rollup which wasn't
        merged yet), there're two possibilities:

        - If one-commit diffs between the remote's ``changes_branch``
          and the local ``changes_branch`` are the same, nothing
          is done. It means that a MR already exists and it has the same
          patch as the one which was just produced locally.
        - If the diffs are different, the remote branch will be deleted,
          effectively closing the old MR, and a new one will be pushed
          instead, and a new MR will be opened.

        The opened MRs are expected to be merged manually.

        :param gitlab_url: A URL to the GitLab instance, e.g.
            ``https://gitlab.example.org``.
        :param full_project_name: Project name within gitlab, e.g.
            ``myorganization/myproject``.
        :param private_token: GitLab access token,
            see `<https://docs.gitlab.com/ce/api/#oauth2-tokens>`_.
        :param mr_title_template: :meth:`str.format` template
            which is used to produce a MR title.
            Available format variables are:

            - ``update_time`` [:class:`datetime.datetime`] -- the time
              of update
            - ``template_meta`` [:class:`.TemplateMeta`] -- template meta
              returned by :meth:`.TemplateVCS.template_meta`
        :param mr_description_markdown_template: :meth:`str.format` template
            which is used to produce a MR description (which will be rendered
            as markdown). Available format variables are:

            - ``update_time`` [:class:`datetime.datetime`] -- the time
              of update
            - ``scaraplate_version`` [:class:`str`] -- scaraplate package
              version
            - ``template_meta`` [:class:`.TemplateMeta`] -- template meta
              returned by :meth:`.TemplateVCS.template_meta`
        :param commit_author: Author name to use for ``git commit``, e.g.
            ``John Doe <john@example.org>``. If ``None``, will be retrieved
            from GitLab as the name of the currently authenticated user
            (using ``private_token``).
        """

        ensure_gitlab_is_installed()
        client = gitlab.Gitlab(url=gitlab_url, private_token=private_token, timeout=30)
        client.auth()

        gitlab_project = client.projects.get(full_project_name)
        project_url = gitlab_project_url(gitlab_url, full_project_name)
        user = client.user
        commit_author = commit_author or f"{user.name} <{user.email}>"

        # pylint wants mandatory arguments to be passed explicitly:
        changes_branch = kwargs.pop("changes_branch")

        with GitCloneProjectVCS.clone(
            clone_url=gitlab_clone_url(project_url, private_token),
            changes_branch=changes_branch,
            commit_author=commit_author,
            **kwargs,
        ) as git_clone:
            yield cls(
                git_clone,
                gitlab_project=gitlab_project,
                mr_title_template=mr_title_template,
                mr_description_markdown_template=mr_description_markdown_template,
            )
