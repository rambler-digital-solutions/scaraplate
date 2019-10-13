import collections.abc
import importlib
from pathlib import Path
from typing import Any, Dict, Mapping, NamedTuple, Optional, Type, Union, cast

import jinja2
import yaml

from .cookiecutter import CookieCutterContext, CookieCutterContextDict, ScaraplateConf
from .gitremotes import GitRemote
from .strategies import Strategy


env = jinja2.Environment(undefined=jinja2.StrictUndefined)


class StrategyNode(NamedTuple):
    strategy: Type[Strategy]
    config: Dict[str, Any]


class ScaraplateYamlOptions(NamedTuple):
    git_remote_type: Optional[Type[GitRemote]]
    cookiecutter_context_type: Type[CookieCutterContext]


class ScaraplateYamlStrategies(NamedTuple):
    default_strategy: StrategyNode
    strategies_mapping: Mapping[str, StrategyNode]


def get_scaraplate_yaml_options(template_path: Path) -> ScaraplateYamlOptions:
    config = yaml.safe_load((template_path / "scaraplate.yaml").read_text())

    git_remote_type_name = config.get("git_remote_type")
    git_remote_type = (
        class_from_str(git_remote_type_name, ensure_subclass=GitRemote)
        if git_remote_type_name is not None
        else None
    )
    assert git_remote_type is None or issubclass(git_remote_type, GitRemote)  # mypy

    cookiecutter_context_type_name = config.get("cookiecutter_context_type")
    cookiecutter_context_type = (
        class_from_str(
            cookiecutter_context_type_name, ensure_subclass=CookieCutterContext
        )
        if cookiecutter_context_type_name is not None
        else cast(Type[CookieCutterContext], ScaraplateConf)  # mypy
    )
    assert cookiecutter_context_type is None or issubclass(
        cookiecutter_context_type, CookieCutterContext
    )  # mypy

    return ScaraplateYamlOptions(
        git_remote_type=git_remote_type,
        cookiecutter_context_type=cookiecutter_context_type,
    )


def get_scaraplate_yaml_strategies(
    template_path: Path, cookiecutter_context_dict: CookieCutterContextDict
) -> ScaraplateYamlStrategies:
    config = yaml.safe_load((template_path / "scaraplate.yaml").read_text())
    default_strategy = _parse_strategy_node(
        "default_strategy", config["default_strategy"]
    )

    strategies_mapping: Dict[str, StrategyNode] = {
        env.from_string(path).render(
            cookiecutter=cookiecutter_context_dict
        ): _parse_strategy_node(str(path), strategy_node)
        for path, strategy_node in config["strategies_mapping"].items()
    }

    return ScaraplateYamlStrategies(
        default_strategy=default_strategy, strategies_mapping=strategies_mapping
    )


def _parse_strategy_node(path: str, raw: Union[str, Dict[str, Any]]) -> StrategyNode:
    if isinstance(raw, str):
        strategy = raw
        config: Dict[str, Any] = {}
    elif isinstance(raw, collections.abc.Mapping):
        strategy_ = raw.get("strategy")
        if not isinstance(strategy_, str):
            raise ValueError(
                f"Unexpected `strategy` value for {path}: "
                f"a string is expected, got {strategy_!r}"
            )
        strategy = strategy_  # mypy

        config = raw.get("config", {})
        if not isinstance(config, collections.abc.Mapping):
            raise ValueError(
                f"Unexpected strategy `config` value for {path}: "
                f"a mapping is expected, got {config!r}"
            )
    else:
        raise ValueError(f"Unexpected strategy value type for {path}: got {raw!r}")

    cls = class_from_str(strategy, ensure_subclass=Strategy)
    assert issubclass(cls, Strategy)  # mypy
    return StrategyNode(strategy=cls, config=config)


def class_from_str(ref: str, *, ensure_subclass: Optional[Type] = None) -> Type[object]:
    if not isinstance(ref, str) or "." not in ref:
        raise ValueError(
            f"A Python class reference must look like "
            f"`mypackage.mymodule.MyClass`, got {ref!r}"
        )
    module_s, cls_s = ref.rsplit(".", 1)
    module = importlib.import_module(module_s)
    cls = getattr(module, cls_s)
    if ensure_subclass is not None and (
        not issubclass(cls, ensure_subclass) or cls is ensure_subclass
    ):
        raise ValueError(f"`{cls}` is not a subclass of {ensure_subclass}")
    return cls
