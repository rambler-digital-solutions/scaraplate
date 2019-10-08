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
    """XXX"""

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
    """XXX"""

    @property
    @abc.abstractmethod
    def dest_path(self) -> Path:
        pass

    @property
    @abc.abstractmethod
    def template_meta(self) -> TemplateMeta:
        pass


class ProjectVCS(abc.ABC):
    """XXX"""

    @property
    @abc.abstractmethod
    def dest_path(self) -> Path:
        pass

    @abc.abstractmethod
    def is_dirty(self) -> bool:
        pass

    @abc.abstractmethod
    def commit_changes(self, template_meta: TemplateMeta) -> None:
        pass
