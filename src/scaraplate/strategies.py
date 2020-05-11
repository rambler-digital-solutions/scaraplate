"""Strategies do the merging between the files from template and the target.

Strategies are specified in the ``scaraplate.yaml`` file located in the root
of the template dir.

Sample ``scaraplate.yaml`` excerpt:

::

    default_strategy: scaraplate.strategies.Overwrite
    strategies_mapping:
      setup.py: scaraplate.strategies.TemplateHash
      src/*/__init__.py: scaraplate.strategies.IfMissing
      package.json:
        strategy: mypackage.mymodule.MyPackageJson
        config:
          my_key: True
      "src/{{ cookiecutter.myvariable }}.md": scaraplate.strategies.IfMissing


The strategy should be an importable Python class which implements
:class:`.Strategy`.

``default_strategy`` and ``strategies_mapping`` keys are the required ones.

The strategy value might be either a string (specifying a Python class),
or a dict of two keys -- ``strategy`` and ``config``. The first form
is just a shortcut for specifying a strategy with an empty config.

``config`` would be passed to the Strategy's ``__init__`` which would
be validated with the inner ``Schema`` class.
"""
import abc
import hashlib
import io
import re
from collections import OrderedDict
from configparser import ConfigParser
from typing import Any, BinaryIO, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Range
from packaging.requirements import Requirement

from . import fields as scaraplate_fields
from .compat import marshmallow_load_data, marshmallow_pass_original_for_many
from .template import TemplateMeta


Pattern = Any  # re.Pattern since py3.7


def detect_newline(
    *file_contents_args: Optional[BinaryIO], default: bytes = b"\n"
) -> bytes:
    for file_contents in file_contents_args:
        if file_contents is None:
            continue
        assert file_contents.tell() == 0
        line_with_newline = file_contents.readline()
        file_contents.seek(0)

        line_without_newline = line_with_newline.rstrip(b"\r\n")
        if len(line_with_newline) != len(line_without_newline):
            # There's a newline at the end of the line -- use it
            newline = line_with_newline[len(line_without_newline) :]
            return newline

    return default


class NoExtraKeysSchema(Schema):
    """Marshmallow schema which raises an error for unknown keys
    in the input.

    Supposedly this won't be needed with marshmallow 3, as this feature
    has been built in,
    see https://marshmallow.readthedocs.io/en/3.0/quickstart.html#handling-unknown-fields  # noqa
    """

    @validates_schema(pass_original=True)
    def check_unknown_fields(self, data, original_data, **kwargs):
        # https://marshmallow.readthedocs.io/en/stable/extending.html#validating-original-input-data  # noqa
        original_data = marshmallow_pass_original_for_many(original_data, self.many)
        for item in original_data:
            unknown = set(item.keys()) - set(self.fields)
            if unknown:
                raise ValidationError({field: "Unknown field" for field in unknown})


class ConfigKeySchema(NoExtraKeysSchema):
    """A key in an INI-like config file."""

    sections = scaraplate_fields.Pattern(required=True)
    keys = scaraplate_fields.Pattern(required=True)


class ConfigSectionSchema(NoExtraKeysSchema):
    """A key in an INI-like config file."""

    sections = scaraplate_fields.Pattern(required=True)
    excluded_keys = scaraplate_fields.Pattern(missing=None)


class Strategy(abc.ABC):
    """The abstract base class for a scaraplate Strategy.

    To implement and use a custom strategy, the following needs to be done:

    1. Create a new Python class which implements :class:`.Strategy`
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
        :param template_meta: Template metadata,
            see :class:`scaraplate.template.TemplateMeta`.
        :param config: The strategy config from ``scaraplate.yaml``.
            It is validated in this ``__init__`` with the inner
            ``Schema`` class.
        """
        self.target_contents = target_contents
        self.template_contents = template_contents
        self.template_meta = template_meta
        self.config = marshmallow_load_data(self.Schema, config)

    @abc.abstractmethod
    def apply(self) -> BinaryIO:
        """Apply the Strategy.

        :return: The resulting file contents which would overwrite
            the target file.
        """
        pass

    class Schema(NoExtraKeysSchema):
        """An empty default schema which doesn't accept any parameters."""


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

    Sample ``scaraplate.yaml`` excerpt:

    ::

        strategies_mapping:
          MANIFEST.in:
            strategy: scaraplate.strategies.SortedUniqueLines
          .gitignore:
            strategy: scaraplate.strategies.SortedUniqueLines
    """

    def apply(self) -> BinaryIO:
        newline = detect_newline(self.target_contents, self.template_contents)

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

        return io.BytesIO(newline.join(map(str.encode, header_lines + sorted_lines)))

    def split_header(self, lines: Sequence[str]) -> Tuple[List[str], List[str]]:
        comment_pattern = self.config["comment_pattern"]
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

        comment_pattern = scaraplate_fields.Pattern(
            missing=re.compile(r"^ *([;#%]|//)")
        )


class TemplateHash(Strategy):
    """A strategy which appends to the target file a git commit hash of
    the template being applied; and the subsequent applications of
    the same template for this file are ignored until the HEAD commit
    of the template changes.

    This strategy is useful when a file needs to be different from
    the template but there's no suitable automated strategy yet,
    so it should be manually resynced on template updates.

    This strategy overwrites the target file on each new commit
    in the template. There's also a :class:`.RenderedTemplateFileHash`
    strategy which does it less frequently: only when the source file
    from the template has changes.

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

    def searched_comment_contents(self) -> List[str]:
        return self.comment_contents()

    def comment_contents(self) -> List[str]:
        line_comment_start = self.config["line_comment_start"]

        comment_lines = [
            f"Generated by https://github.com/rambler-digital-solutions/scaraplate"
        ]
        if self.template_meta.is_git_dirty:
            comment_lines.append(f"From (dirty) {self.template_meta.commit_url}")
        else:
            comment_lines.append(f"From {self.template_meta.commit_url}")

        return [f"{line_comment_start} {line}" for line in comment_lines]

    def render_comment(self, comment_lines: Sequence[str], *, newline: bytes) -> bytes:
        comment_lines = [self._maybe_add_linter_ignore(line) for line in comment_lines]
        return b"".join(line.encode("ascii") + newline for line in comment_lines)

    def _maybe_add_linter_ignore(self, line: str) -> str:
        line_length = self.config["max_line_length"]
        ignore_mark = self.config["max_line_linter_ignore_mark"]
        if line_length and len(line) >= line_length:
            return f"{line}{ignore_mark}"
        return line

    def apply(self) -> BinaryIO:
        newline = detect_newline(self.target_contents, self.template_contents)

        searched_comment = self.render_comment(
            self.searched_comment_contents(), newline=newline
        )
        appended_comment = self.render_comment(self.comment_contents(), newline=newline)
        if self.target_contents is not None:
            target_text = self.target_contents.read()
            if searched_comment in target_text and not self.template_meta.is_git_dirty:
                # Hash hasn't changed -- keep the target.
                self.target_contents.seek(0)
                return self.target_contents

        # Convert template newlines to the target file newlines:
        template_lines = self.template_contents.read().splitlines()
        out_bytes = b"".join(line + newline for line in template_lines)

        out_bytes += newline + appended_comment
        return io.BytesIO(out_bytes)

    class Schema(NoExtraKeysSchema):
        """Allowed params:

        - ``line_comment_start`` [``#``] -- The prefix which should be used
          to start a line comment.
        - ``max_line_length`` [`None`] -- The maximum line length for
          the appended line comments after which
          the ``max_line_linter_ignore_mark`` suffix should be added.
        - ``max_line_linter_ignore_mark`` [``# noqa``] -- The linter's
          line ignore mark for the appended line comments which are
          longer than ``max_line_length`` columns. The default ``# noqa``
          mark silences ``flake8``.
        """

        line_comment_start = fields.String(missing="#")
        max_line_length = fields.Int(missing=None, validate=Range(min=10))
        max_line_linter_ignore_mark = fields.String(missing="  # noqa")


class RenderedTemplateFileHash(TemplateHash):
    """A strategy which appends to the target file a hash of
    the rendered template file; and the subsequent applications of
    the same template for this file are ignored until the rendered
    file has changes.

    This strategy is similar to :class:`.TemplateHash` with the difference
    that the target file is rewritten less frequently: only when
    the hash of the source file from the template is changed.

    .. versionadded:: 0.2

    Sample ``scaraplate.yaml`` excerpt:

    ::

        strategies_mapping:
            setup.py:
              strategy: scaraplate.strategies.RenderedTemplateFileHash
              config:
                line_comment_start: '#'
                max_line_length: 87
                max_line_linter_ignore_mark: '  # noqa'
            Jenkinsfile:
              strategy: scaraplate.strategies.RenderedTemplateFileHash
              config:
                line_comment_start: '//'

    This would result in the following:

    setup.py:

    ::

        ...file contents...

        # Generated by https://github.com/rambler-digital-solutions/scaraplate
        # RenderedTemplateFileHash d2671228e3dfc3e663bfaf9b5b151ce8
        # From https://github.com/rambler-digital-solutions/scaraplate-example-template/commit/1111111111111111111111111111111111111111  # noqa

    Jenkinsfile:

    ::

        ...file contents...

        // Generated by https://github.com/rambler-digital-solutions/scaraplate
        // RenderedTemplateFileHash d2as1228eb7233e663bfaf9b5b151ce8
        // From https://github.com/rambler-digital-solutions/scaraplate-example-template/commit/1111111111111111111111111111111111111111

    """

    def searched_comment_contents(self) -> List[str]:
        line_comment_start = self.config["line_comment_start"]

        rendered_template_file_hash = hashlib.md5(
            self.template_contents.read()
        ).hexdigest()
        self.template_contents.seek(0)
        comment_lines = [
            f"Generated by https://github.com/rambler-digital-solutions/scaraplate",
            f"RenderedTemplateFileHash {rendered_template_file_hash}",
        ]

        return [f"{line_comment_start} {line}" for line in comment_lines]

    def comment_contents(self) -> List[str]:
        line_comment_start = self.config["line_comment_start"]

        comment_lines = []
        if self.template_meta.is_git_dirty:
            comment_lines.append(f"From (dirty) {self.template_meta.commit_url}")
        else:
            comment_lines.append(f"From {self.template_meta.commit_url}")

        return self.searched_comment_contents() + [
            f"{line_comment_start} {line}" for line in comment_lines
        ]


class ConfigParserMerge(Strategy):
    """A strategy which merges INI-like files (with :mod:`configparser`).

    The resulting file is the one from the template with
    the following modifications:

    - Comments are stripped
    - INI file is reformatted (whitespaces are cleaned, sections
      and keys are sorted)
    - Sections specified in the ``preserve_sections`` config list are
      preserved from the target file.
    - Keys specified in the ``preserve_keys`` config list are
      preserved from the target file.

    This strategy cannot be used to merge config files which contain
    keys without a preceding section declaration
    (e.g. ``.editorconfig`` won't work).

    Sample ``scaraplate.yaml`` excerpt:

    ::

        strategies_mapping:
          .pylintrc:
            strategy: scaraplate.strategies.ConfigParserMerge
            config:
              preserve_sections: []
              preserve_keys:
              - sections: ^MASTER$
                keys: ^extension-pkg-whitelist$
              - sections: ^TYPECHECK$
                keys: ^ignored-

          tox.ini:
            strategy: scaraplate.strategies.ConfigParserMerge
            config:
              preserve_sections:
              - sections: ^tox$
              preserve_keys:
              - sections: ^testenv
                keys: ^extras$

          pytest.ini:
            strategy: scaraplate.strategies.ConfigParserMerge
            config:
              preserve_sections: []
              preserve_keys:
              - sections: ^pytest$
                keys: ^python_files$

          .isort.cfg:
            strategy: scaraplate.strategies.ConfigParserMerge
            config:
              preserve_sections: []
              preserve_keys:
              - sections: ^settings$
                keys: ^known_third_party$
    """

    def apply(self) -> BinaryIO:
        newline = detect_newline(self.target_contents, self.template_contents)

        template_parser = self.parse_config(self.template_contents, source="<template>")

        target_parser: Optional[ConfigParser] = None

        if self.target_contents is not None:
            target_parser = self.parse_config(self.target_contents, source="<target>")

        self.merge_configs(template_parser, target_parser, newline=newline)

        return self.parser_to_pretty_output(template_parser, newline=newline)

    def parse_config(self, data: BinaryIO, source: str) -> ConfigParser:
        # We don't need to treat the `[DEFAULT]` section as actually
        # a one which provides defaults to other sections, so we disable
        # this by mocking the `default_section`.
        parser = ConfigParser(
            default_section="__scaraplate_internal_nonexisting_default"
        )

        text = data.read().decode()
        # Configparser doesn't like \r\n and \r newlines, so let's replace
        # them explicitly:
        text = "".join(f"{line}\n" for line in text.splitlines())
        parser.read_string(text, source=source)
        return parser

    def merge_configs(
        self,
        template_parser: ConfigParser,
        target_parser: Optional[ConfigParser],
        *,
        newline: bytes,
    ) -> None:
        if target_parser is None:
            return

        for ini_key in self.config["preserve_sections"]:
            self.maybe_preserve_sections(
                template_parser,
                target_parser,
                ini_key["sections"],
                ini_key["excluded_keys"],
            )

        for ini_key in self.config["preserve_keys"]:
            self.maybe_preserve_key(
                template_parser, target_parser, ini_key["sections"], ini_key["keys"]
            )

    def maybe_preserve_key(
        self,
        template_parser: ConfigParser,
        target_parser: ConfigParser,
        sections_pattern: Pattern,
        keys_pattern: Pattern,
    ) -> None:
        for section in target_parser.sections():
            if sections_pattern.match(section):
                for key, value in target_parser[section].items():
                    if keys_pattern.match(key):
                        self.ensure_section(template_parser, section)
                        template_parser[section][key] = value

    def maybe_preserve_sections(
        self,
        template_parser: ConfigParser,
        target_parser: ConfigParser,
        sections_pattern: Pattern,
        ignore_keys_pattern: Optional[Pattern],
    ) -> None:
        for section in target_parser.sections():
            if sections_pattern.match(section):
                section_data = dict(target_parser[section])

                if ignore_keys_pattern is not None:
                    for key, value in template_parser[section].items():
                        if ignore_keys_pattern.match(key):
                            section_data[key] = value

                template_parser[section] = section_data

    def ensure_section(self, parser: ConfigParser, section: str) -> None:
        if not parser.has_section(section):
            parser.add_section(section)

    def parser_to_pretty_output(
        self, parser: ConfigParser, *, newline: bytes
    ) -> BinaryIO:
        parser = self._sorted_configparser(parser)

        content = self._parser_to_str(parser).replace("\t", " " * 4)

        acc = []
        for line in content.splitlines():
            acc.append(line.rstrip())
        new_contents = newline.join(map(str.encode, acc))
        return io.BytesIO(new_contents)

    def _sorted_configparser(self, parser: ConfigParser) -> ConfigParser:
        out = ConfigParser(dict_type=OrderedDict)  # type: ignore

        # `out.read_dict(parser)` might not work here as expected: the keys from
        # the `[DEFAULT]` section would be set in *all* sections instead of
        # just the `[DEFAULT]` one.
        out.read_string(self._parser_to_str(parser))

        for section in out._sections:  # type: ignore
            section_ = OrderedDict(
                sorted(out._sections[section].items())  # type: ignore
            )
            out._sections[section] = section_  # type: ignore

        out._sections = OrderedDict(sorted(out._sections.items()))  # type: ignore
        return out

    def _parser_to_str(self, parser: ConfigParser) -> str:
        buffer = io.StringIO()
        parser.write(buffer)
        return buffer.getvalue()

    class Schema(NoExtraKeysSchema):
        """Allowed params:

        - ``preserve_keys`` (required) -- the list of config keys
          which should be preserved from the target file. Values schema:

            + ``sections`` (required) -- a PCRE pattern matching
              sections containing the keys to preserve.
            + ``keys`` (required) -- a PCRE pattern matching keys
              in the matched sections.

        - ``preserve_sections`` (required) -- the list of config sections
          which should be preserved from the target file. If the matching
          section exists in the template, it would be fully overwritten.
          Values schema:

            + ``sections`` (required) -- a PCRE pattern matching
              sections which should be preserved from the target.
            + ``excluded_keys`` [`None`] -- a PCRE pattern matching
              the keys which should not be overwritten in the template
              when preserving the section.

        """

        preserve_keys = fields.Nested(ConfigKeySchema, many=True, required=True)
        preserve_sections = fields.Nested(ConfigSectionSchema, many=True, required=True)


class SetupCfgMerge(ConfigParserMerge):
    r"""A strategy which merges the Python's ``setup.cfg`` file.

    Based on the :class:`.ConfigParserMerge` strategy, additionally
    containing a ``merge_requirements`` config option for merging
    the lists of Python requirements between the files.

    Sample ``scaraplate.yaml`` excerpt:

    ::

        strategies_mapping:
          setup.cfg:
            strategy: scaraplate.strategies.SetupCfgMerge
            config:
              merge_requirements:
              - sections: ^options$
                keys: ^install_requires$
              - sections: ^options\.extras_require$
                keys: ^develop$
              preserve_keys:
              - sections: ^tool:pytest$
                keys: ^testpaths$
              - sections: ^build$
                keys: ^executable$
              preserve_sections:
              - sections: ^mypy-
              - sections: ^options\.data_files$
              - sections: ^options\.entry_points$
              - sections: ^options\.extras_require$
    """

    class Schema(ConfigParserMerge.Schema):
        __doc__ = (
            ConfigParserMerge.Schema.__doc__  # type: ignore
            + """

        - ``merge_requirements`` (required) -- the list of config
          keys containing the lists of Python requirements which should
          be merged together. Values schema:

            + ``sections`` (required) -- a PCRE pattern matching
              sections containing the keys with requirements.
            + ``keys`` (required) -- a PCRE pattern matching keys
              in the matched sections.
        """  # type: ignore
        )

        merge_requirements = fields.Nested(ConfigKeySchema, many=True, required=True)

    def merge_configs(
        self,
        template_parser: ConfigParser,
        target_parser: Optional[ConfigParser],
        *,
        newline: bytes,
    ) -> None:
        keys: Set[Tuple[str, str]] = set()

        for ini_key in self.config["merge_requirements"]:
            if target_parser is not None:
                for section in target_parser.sections():
                    if ini_key["sections"].match(section):
                        for key, value in target_parser[section].items():
                            if ini_key["keys"].match(key):
                                keys.add((section, key))

            for section in template_parser.sections():
                if ini_key["sections"].match(section):
                    for key, value in template_parser[section].items():
                        if ini_key["keys"].match(key):
                            keys.add((section, key))

        for section, key in keys:
            self._merge_requirements(
                template_parser, target_parser, section, key, newline=newline
            )

        super().merge_configs(template_parser, target_parser, newline=newline)

    def _merge_requirements(
        self,
        template_parser: ConfigParser,
        target_parser: Optional[ConfigParser],
        section: str,
        key: str,
        *,
        newline: bytes,
    ) -> None:
        "Merge in the requirements from template to the target."

        template_requirements = self._parse_requirements(template_parser, section, key)
        if target_parser is not None:
            target_requirements = self._parse_requirements(target_parser, section, key)
        else:
            target_requirements = []

        def normalize_requirement(requirement):
            return self._requirement_name(requirement).lower()

        existing_requirement_names = set(
            map(normalize_requirement, target_requirements)
        )
        wanted_requirements = target_requirements

        for requirement in template_requirements:
            name = normalize_requirement(requirement)
            if name not in existing_requirement_names:
                wanted_requirements.append(requirement)

        wanted_requirements = sorted(wanted_requirements, key=str.casefold)

        result = self._dump_setupcfg_requirements(wanted_requirements, newline=newline)

        self.ensure_section(template_parser, section)
        template_parser[section][key] = result

        if target_parser is not None:
            self.ensure_section(target_parser, section)
            target_parser[section][key] = result

    def _parse_requirements(
        self, parser: ConfigParser, section: str, key: str
    ) -> List[str]:
        try:
            requirements = parser[section][key]
        except KeyError:
            return []

        return self._parse_setupcfg_requirements(requirements)

    def _parse_setupcfg_requirements(self, requirements: str) -> List[str]:
        return [r for r in map(str.strip, requirements.split()) if r]

    def _requirement_name(self, full_requirement: str) -> str:
        requirement = Requirement(full_requirement)
        return requirement.name

    def _dump_setupcfg_requirements(
        self, requirements: Iterable[str], *, newline: bytes
    ) -> str:
        # Leave first element empty to produce nicer cfg lists like:
        #   install_requires =
        #       foo==1.0.0
        #       bar==2.0.0
        # instead of
        #   install_requires = foo==1.0.0
        #       bar==2.0.0
        acc = [""] + [item for item in requirements]
        return newline.decode().join(acc)
