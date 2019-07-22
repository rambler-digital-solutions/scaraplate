"""Strategies do the merging between the files from template and the target.

Strategies are specified in a ``scaraplate.yaml`` file located in the root
of the template git repo.

``scaraplate.yaml`` might look like this:

::

    default_strategy: scaraplate.strategies.Overwrite
    strategies_mapping:
      Jenkinsfile: scaraplate.strategies.TemplateHash
      package.json:
        strategy: mypackage.mymodule.MyPackageJson
        config:
          my_key: True


The strategy should be an importable Python class which extends
:class:`.Strategy`.

``config`` would be passed to the Strategy's ``__init__`` which would
be validated with the inner ``Schema`` class.
"""
import abc
import io
import re
from configparser import ConfigParser
from typing import Any, BinaryIO, Dict, List, Optional, Sequence, Tuple

from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Range

from .parsers import (
    dump_setupcfg_requirements,
    parse_setupcfg_requirements,
    parser_to_pretty_output,
    pylintrc_parser,
    requirement_name,
    setup_cfg_parser,
)
from .template import TemplateMeta


def _ensure_section(parser: ConfigParser, section: str) -> None:
    if not parser.has_section(section):
        parser.add_section(section)


def _validate_pattern(value: str) -> bool:
    try:
        re.compile(value)
    except re.error:
        return False
    else:
        return True


class NoExtraKeysSchema(Schema):
    """Marshmallow schema which raises an error for unknown keys
    in the input.

    Supposedly this won't be needed with marshmallow 3, as this feature
    has been built in,
    see https://marshmallow.readthedocs.io/en/3.0/quickstart.html#handling-unknown-fields  # noqa
    """

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, data, original_data):
        # https://marshmallow.readthedocs.io/en/stable/extending.html#validating-original-input-data  # noqa
        unknown = set(original_data) - set(self.fields)
        if unknown:
            raise ValidationError("Unknown field", unknown)


class Strategy(abc.ABC):
    """The abstract base class for a scaraplate Strategy.

    To implement and use a custom strategy, the following needs to be done:

    1. Create a new Python class which extends :class:`.Strategy`
    2. Override the inner ``Schema`` class if you need
       to configure your strategy from ``scaraplate.yaml``.
    3. Implement the ``apply`` method.

    Assuming that the new strategy class is importable in the Python
    environment in which scaraplate is run, to use the strategy
    you need to specify it in ``scaraplate.yaml``, e.g.

    ::

        strategies_mapping:
          myfile.txt: mypackage.mymodule.MyStrategy

    """

    def __init__(
        self,
        *,
        target_contents: Optional[BinaryIO],
        template_contents: BinaryIO,
        template_meta: TemplateMeta,
        config: Dict[str, Any],
    ) -> None:
        """Init the strategy.

        :param target_contents: The file contents in the target project.
            ``None`` if the file doesn't exist.
        :param template_contents: The file contents from the template
            (after cookiecutter is applied).
        :param template_meta: Template metadata: the current git commit,
            git remote url and so on.
        :param config: The strategy config from ``scaraplate.yaml``.
            It is validated in this ``__init__`` with the inner
            ``Schema`` class.
        """
        self.target_contents = target_contents
        self.template_contents = template_contents
        self.template_meta = template_meta
        self.config = self.Schema(strict=True).load(config).data

    @abc.abstractmethod
    def apply(self) -> BinaryIO:
        """Apply the Strategy.

        :return: The resulting file contents which would overwrite
            the target file.
        """
        pass

    class Schema(NoExtraKeysSchema):
        """A default empty schema which doesn't allow any parameters."""


class Overwrite(Strategy):
    """A simple strategy which always overwrites the target files
    with the ones from the template.
    """

    def apply(self) -> BinaryIO:
        return self.template_contents


class IfMissing(Strategy):
    """A strategy which writes the file from the template only
    if it doesn't exist in target.
    """

    def apply(self) -> BinaryIO:
        if self.target_contents is None:
            return self.template_contents
        else:
            return self.target_contents


class SortedUniqueLines(Strategy):
    """A strategy which combines both template and target files,
    sorts the combined lines and keeps only unique ones.

    However, the comments in the beginning of the files are treated
    differently. They would be stripped from the target and replaced
    with the ones from the template. The most common usecase for this
    are the License headers.
    """

    def apply(self) -> BinaryIO:
        header_lines, out_lines = self.split_header(
            self.template_contents.read().decode().splitlines()
        )
        if self.target_contents is not None:
            # Header from the target is ignored: it will be overridden
            # with template.
            _, target_lines = self.split_header(
                self.target_contents.read().decode().splitlines()
            )
            out_lines.extend(target_lines)

        # Keep unique lines and sort them.
        #
        # Note that `set` is not guaranteed to preserve the original
        # order, so we need to compare by both casefolded str and
        # the original to ensure the stable order for the same strings
        # written in different cases.
        sorted_lines = sorted(set(out_lines), key=lambda s: (s.casefold(), s))

        sorted_lines = [line for line in sorted_lines if line]
        sorted_lines.append("")  # trailing newline

        return io.BytesIO("\n".join(header_lines + sorted_lines).encode())

    def split_header(self, lines: Sequence[str]) -> Tuple[List[str], List[str]]:
        comment_pattern = re.compile(self.config["comment_pattern"])
        it = iter(lines)

        header_lines = []
        to_sort_lines = []
        for line in it:
            if comment_pattern.match(line) is not None or not line.strip():
                header_lines.append(line)
            else:
                to_sort_lines.append(line)
                break
        to_sort_lines.extend(it)

        return header_lines, to_sort_lines

    class Schema(NoExtraKeysSchema):
        r"""Allowed params:

        - ``comment_pattern`` [``^ *([;#%]|//)``] -- a PCRE pattern which should
          match the line with a comment.
        """

        comment_pattern = fields.String(
            missing=r"^ *([;#%]|//)", validate=[_validate_pattern]
        )


class TemplateHash(Strategy):
    """A strategy which appends to the target file a git commit hash of
    the template being applied; and the subsequent applications of
    the same template for this file are ignored.

    This strategy is useful when a file needs to be different from
    the template, yet it should be manually resynced on template updates.

    Sample ``scaraplate.yaml`` excerpt:

    ::

        strategies_mapping:
          setup.py:
            strategy: scaraplate.strategies.TemplateHash
            config:
              line_comment_start: '#'
              max_line_length: 87
              max_line_linter_ignore_mark: '  # noqa'
          Jenkinsfile:
            strategy: scaraplate.strategies.TemplateHash
            config:
              line_comment_start: '//'

    This would result in the following:

    setup.py:

    ::

        ...file contents...

        # Generated by https://github.com/rambler-digital-solutions/scaraplate
        # From https://github.com/rambler-digital-solutions/scaraplate-example-template/commit/1111111111111111111111111111111111111111  # noqa

    Jenkinsfile:

    ::

        ...file contents...

        // Generated by https://github.com/rambler-digital-solutions/scaraplate
        // From https://github.com/rambler-digital-solutions/scaraplate-example-template/commit/1111111111111111111111111111111111111111

    """

    def comment_contents(self) -> str:
        line_comment_start = self.config["line_comment_start"]

        comment_lines = [f"Generated by https://github.com/rambler-digital-solutions/scaraplate"]
        if self.template_meta.is_git_dirty:
            comment_lines.append(f"From (dirty) {self.template_meta.commit_url}")
        else:
            comment_lines.append(f"From {self.template_meta.commit_url}")

        return "".join(f"{line_comment_start} {line}\n" for line in comment_lines)

    def comment(self) -> str:
        comment = self.comment_contents()
        comment_lines = comment.split("\n")
        comment_lines = [self._maybe_add_linter_ignore(line) for line in comment_lines]
        return "\n".join(comment_lines)

    def _maybe_add_linter_ignore(self, line: str) -> str:
        line_length = self.config["max_line_length"]
        ignore_mark = self.config["max_line_linter_ignore_mark"]
        if line_length and len(line) >= line_length:
            return f"{line}{ignore_mark}"
        return line

    def apply(self) -> BinaryIO:
        comment = self.comment().encode("ascii")
        if self.target_contents is not None:
            target_text = self.target_contents.read()
            if comment in target_text and not self.template_meta.is_git_dirty:
                # Hash hasn't changed -- keep the target.
                self.target_contents.seek(0)
                return self.target_contents

        out_bytes = self.template_contents.read()
        out_bytes += b"\n" + comment  # TODO detect newlines type?
        return io.BytesIO(out_bytes)

    class Schema(NoExtraKeysSchema):
        """Allowed params:

        - ``line_comment_start`` [``#``] -- The prefix which should be used
          to start a line comment.
        - ``max_line_length`` [`None`] -- The maximum line length for
          the new line comments after which the ``max_line_linter_ignore_mark``
          suffix should be appended.
        - ``max_line_linter_ignore_mark`` [``# noqa``] -- The linter's
          line ignore mark for the new comment lines longer than
          ``max_line_length`` columns. The default ``# noqa`` mark
          silences ``flake8``.
        """

        line_comment_start = fields.String(missing="#")
        max_line_length = fields.Int(missing=None, validate=Range(min=10))
        max_line_linter_ignore_mark = fields.String(missing="  # noqa")


class PylintrcMerge(Strategy):
    """A strategy which merges ``.pylintrc`` between a template
    and the target project.

    The resulting ``.pylintrc`` is the one from the template with
    the following modifications:

    - Comments are stripped
    - INI file is reformatted (whitespaces are cleaned, sections
      and values are sorted)
    - ``ignored-*`` keys of the ``[TYPECHECK]`` section are taken from
      the target ``.pylintrc``.
    """

    def apply(self) -> BinaryIO:
        template_parser = pylintrc_parser(
            self.template_contents, source=".pylintrc.template"
        )

        if self.target_contents is not None:
            target_parser = pylintrc_parser(
                self.target_contents, source=".pylintrc.target"
            )
            self._maybe_preserve_key(
                template_parser, target_parser, "MASTER", "extension-pkg-whitelist"
            )
            self._maybe_preserve_key(
                template_parser, target_parser, "TYPECHECK", "ignored-modules"
            )
            self._maybe_preserve_key(
                template_parser, target_parser, "TYPECHECK", "ignored-classes"
            )

        return parser_to_pretty_output(template_parser)

    def _maybe_preserve_key(
        self,
        template_parser: ConfigParser,
        target_parser: ConfigParser,
        section: str,
        key: str,
    ) -> None:
        try:
            target = target_parser[section][key]
        except KeyError:
            # No such section/value in target -- keep the one that is
            # in the template.
            return
        else:
            _ensure_section(template_parser, section)
            template_parser[section][key] = target


class SetupcfgMerge(Strategy):
    """A strategy which merges the Python's ``setup.cfg`` file."""

    def apply(self) -> BinaryIO:
        template_parser = setup_cfg_parser(
            self.template_contents, source="setup.cfg.template"
        )

        target_parser = None

        if self.target_contents is not None:
            target_parser = setup_cfg_parser(
                self.target_contents, source="setup.cfg.target"
            )

            self._maybe_preserve_sections(
                template_parser,
                target_parser,
                # A non-standard section
                re.compile("^freebsd$"),
            )

            self._maybe_preserve_sections(
                template_parser,
                target_parser,
                # A non-standard section
                re.compile("^infra.dependencies_updater$"),
            )

            self._maybe_preserve_sections(
                template_parser, target_parser, re.compile("^mypy-")
            )

            self._maybe_preserve_sections(
                template_parser, target_parser, re.compile("^options.data_files$")
            )

            self._maybe_preserve_sections(
                template_parser, target_parser, re.compile("^options.entry_points$")
            )

            self._maybe_preserve_sections(
                template_parser,
                target_parser,
                re.compile("^options.extras_require$"),
                ignore_keys_pattern=re.compile("^develop$"),
            )

            self._maybe_preserve_key(
                template_parser, target_parser, "tool:pytest", "testpaths"
            )

            # TODO verify if this is still relevant:
            self._maybe_preserve_key(
                template_parser, target_parser, "build", "executable"
            )

        self._merge_requirements(
            template_parser, target_parser, "options.extras_require", "develop"
        )

        self._merge_requirements(
            template_parser, target_parser, "options", "install_requires"
        )

        return parser_to_pretty_output(template_parser)

    def _maybe_preserve_sections(
        self,
        template_parser: ConfigParser,
        target_parser: ConfigParser,
        sections_pattern: Any,  # re.Pattern since py3.7
        ignore_keys_pattern: Any = None,
    ) -> None:
        for section in target_parser.sections():  # default section is ignored
            if sections_pattern.match(section):
                section_data = dict(target_parser[section])

                if ignore_keys_pattern is not None:
                    for key, value in template_parser[section].items():
                        if ignore_keys_pattern.match(key):
                            section_data[key] = value

                template_parser[section] = section_data

    def _merge_requirements(
        self,
        template_parser: ConfigParser,
        target_parser: Optional[ConfigParser],
        section: str,
        key: str,
    ) -> None:
        "Merge in the requirements from template to the target."

        template_requirements = self._parse_requirements(template_parser, section, key)
        if target_parser is not None:
            target_requirements = self._parse_requirements(target_parser, section, key)
        else:
            target_requirements = []

        def normalize_requirement(requirement):
            return requirement_name(requirement).lower()

        existing_requirement_names = set(
            map(normalize_requirement, target_requirements)
        )
        wanted_requirements = target_requirements

        for requirement in template_requirements:
            name = normalize_requirement(requirement)
            if name not in existing_requirement_names:
                wanted_requirements.append(requirement)

        wanted_requirements = sorted(wanted_requirements, key=str.casefold)

        _ensure_section(template_parser, section)
        template_parser[section][key] = dump_setupcfg_requirements(wanted_requirements)

    def _parse_requirements(
        self, parser: ConfigParser, section: str, key: str
    ) -> List[str]:
        try:
            requirements = parser[section][key]
        except KeyError:
            return []

        return parse_setupcfg_requirements(requirements)

    def _maybe_preserve_key(
        self,
        template_parser: ConfigParser,
        target_parser: ConfigParser,
        section: str,
        key: str,
    ) -> None:
        try:
            target = target_parser[section][key]
        except KeyError:
            # No such section/value in target -- keep the one that is
            # in the template.
            return
        else:
            _ensure_section(template_parser, section)
            template_parser[section][key] = target
