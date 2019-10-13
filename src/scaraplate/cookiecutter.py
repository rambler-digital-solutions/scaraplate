"""cookiecutter context are the variables specified in ``cookiecutter.json``,
which should be provided to cookiecutter to cut a project from the template.

The context should be generated by one of the files in the template,
so scaraplate could read these variables and rollup the template automatically
(i.e. without asking for these variables).

The default context reader is :class:`.ScaraplateConf`, but a custom one
might be specified in ``scaraplate.yaml`` like this:

::

    cookiecutter_context_type: scaraplate.cookiecutter.SetupCfg
"""
import abc
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, NewType


CookieCutterContextDict = NewType("CookieCutterContextDict", Dict[str, str])


def _configparser_from_path(cfg_path: Path) -> ConfigParser:
    parser = ConfigParser()
    text = cfg_path.read_text()
    parser.read_string(text, source=str(cfg_path))
    return parser


class CookieCutterContext(abc.ABC):
    """The abstract base class for retrieving cookiecutter context from
    the target project.

    This class can be extended to provide a custom implementation of
    the context reader.
    """

    def __init__(self, target_path: Path) -> None:
        """Init the context reader."""
        self.target_path = target_path

    @abc.abstractmethod
    def read(self) -> CookieCutterContextDict:
        """Retrieve the context.

        If the target file doesn't exist, :class:`FileNotFoundError`
        must be raised.

        If the file doesn't contain the context, an empty dict
        should be returned.
        """
        pass


class ScaraplateConf(CookieCutterContext):
    """A default context reader which assumes that the cookiecutter
    template contains the following file named ``.scaraplate.conf``
    in the root of the project dir:

    ::

        [cookiecutter_context]
        {%- for key, value in cookiecutter.items()|sort %}
        {{ key }} = {{ value }}
        {%- endfor %}

    Cookiecutter context would be rendered in the target project by this
    file, and this class is able to retrieve that context from it.
    """

    section_name = "cookiecutter_context"

    def __init__(self, target_path: Path) -> None:
        super().__init__(target_path)
        self.scaraplate_conf = target_path / ".scaraplate.conf"

    def read(self) -> CookieCutterContextDict:
        configparser = _configparser_from_path(self.scaraplate_conf)
        context_configparser = dict(configparser).get(self.section_name)
        context = dict(context_configparser or {})
        return CookieCutterContextDict(context)

    def __str__(self):
        return f"{self.scaraplate_conf}"


class SetupCfg(CookieCutterContext):
    """A context reader which retrieves the cookiecutter context from
    a section in ``setup.cfg`` file.

    The ``setup.cfg`` file must be in the cookiecutter template and must
    contain the following section:

    ::

        [tool:cookiecutter_context]
        {%- for key, value in cookiecutter.items()|sort %}
        {{ key }} = {{ value }}
        {%- endfor %}
    """

    section_name = "tool:cookiecutter_context"

    def __init__(self, target_path: Path) -> None:
        super().__init__(target_path)
        self.setup_cfg = target_path / "setup.cfg"

    def read(self) -> CookieCutterContextDict:
        configparser = _configparser_from_path(self.setup_cfg)
        context_configparser = dict(configparser).get(self.section_name)
        context = dict(context_configparser or {})
        return CookieCutterContextDict(context)

    def __str__(self):
        return f"{self.setup_cfg}"
