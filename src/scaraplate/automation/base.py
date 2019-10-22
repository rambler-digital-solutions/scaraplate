import abc
import logging
from contextlib import ExitStack
from pathlib import Path
from typing import ContextManager, Mapping, Optional

from scaraplate.rollup import rollup
from scaraplate.template import TemplateMeta


logger = logging.getLogger("scaraplate")

__all__ = ("TemplateVCS", "ProjectVCS", "automatic_rollup")


def automatic_rollup(
    *,
    template_vcs_ctx: ContextManager["TemplateVCS"],
    project_vcs_ctx: ContextManager["ProjectVCS"],
    extra_context: Optional[Mapping[str, str]] = None
) -> None:
    """The main function of the automated rollup implementation.

    This function accepts two context managers, which should return
    two classes: :class:`.TemplateVCS` and :class:`.ProjectVCS`,
    which represent the cloned template and target project
    correspondingly.

    The context managers should prepare the repos, e.g. they should
    create a temporary directory, clone a repo there, and produce
    a :class:`.TemplateVCS` or :class:`.ProjectVCS` class instance.

    This function then applies scaraplate rollup of the template
    to the target project in :ref:`no-input mode <no_input_mode>`.
    If the target project contains any changes (as reported by
    :meth:`.ProjectVCS.is_dirty`), they will be committed by calling
    :meth:`.ProjectVCS.commit_changes`.

    .. versionadded:: 0.2
    """

    with ExitStack() as stack:
        # Clone target project and template
        project_vcs = stack.enter_context(project_vcs_ctx)
        template_vcs = stack.enter_context(template_vcs_ctx)

        rollup(
            template_dir=template_vcs.dest_path,
            target_project_dir=project_vcs.dest_path,
            no_input=True,
            extra_context=extra_context,
        )

        if not project_vcs.is_dirty():
            logger.info(
                "scaraplate rollup didn't change anything -- the project "
                "is in sync with template"
            )
            return

        logger.info("scaraplate rollup produced some changes -- committing them...")
        project_vcs.commit_changes(template_vcs.template_meta)
        logger.info("scaraplate changes have been committed successfully")


class TemplateVCS(abc.ABC):
    """A base class representing a template retrieved from a VCS
    (probably residing in a temporary directory).

    The resulting directory with template must be within a git repository,
    see :doc:`template` for details. But it doesn't mean that it must
    be retrieved from git. Template might be retrieved from anywhere,
    it just has to be in git at the end. That git repo will be used
    to fill the :class:`.TemplateMeta` structure.
    """

    @property
    @abc.abstractmethod
    def dest_path(self) -> Path:
        """Path to the root directory of the template."""
        pass

    @property
    @abc.abstractmethod
    def template_meta(self) -> TemplateMeta:
        """:class:`.TemplateMeta` filled using the template's git repo."""
        pass


class ProjectVCS(abc.ABC):
    """A base class representing a project retrieved from a VCS
    (probably residing in a temporary directory).

    The project might use any VCS, at this point there're no assumptions
    made by scaraplate about the VCS.
    """

    @property
    @abc.abstractmethod
    def dest_path(self) -> Path:
        """Path to the root directory of the project."""
        pass

    @abc.abstractmethod
    def is_dirty(self) -> bool:
        """Tell whether the project has any changes not committed
        to the VCS."""
        pass

    @abc.abstractmethod
    def commit_changes(self, template_meta: TemplateMeta) -> None:
        """Commit the changes made to the project. This method is
        responsible for delivering the changes back to the place
        the project was retrieved from. For example, if the project
        is using ``git`` and it was cloned to a temporary directory,
        then this method should commit the changes and push them back
        to git remote.

        This method will be called only if :meth:`.ProjectVCS.is_dirty`
        has returned True.
        """
        pass
