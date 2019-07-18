import collections.abc
import importlib
from pathlib import Path
from typing import Any, Dict, Mapping, NamedTuple, Type, Union

import yaml

from .strategies import Strategy


class StrategyNode(NamedTuple):
    strategy: Type[Strategy]
    config: Dict[str, Any]


class ScaraplateYaml(NamedTuple):
    default_strategy: StrategyNode
    strategies_mapping: Mapping[str, StrategyNode]


def get_scaraplate_yaml(template_path: Path) -> ScaraplateYaml:
    config = yaml.safe_load((template_path / "scaraplate.yaml").read_text())
    default_strategy = _parse_strategy_node(
        "default_strategy", config["default_strategy"]
    )

    strategies_mapping: Dict[str, StrategyNode] = {
        str(path): _parse_strategy_node(str(path), strategy_node)
        for path, strategy_node in config["strategies_mapping"].items()
    }

    return ScaraplateYaml(
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

    cls = class_from_str(strategy)
    if not issubclass(cls, Strategy) or cls is Strategy:
        raise ValueError(
            f"`{cls}` is not a subclass of `scaraplate.strategies.Strategy`"
        )
    return StrategyNode(strategy=cls, config=config)


def class_from_str(ref: str) -> Type[object]:
    if "." not in ref:
        raise ValueError(
            f"A Python class reference must look like "
            f"`mypackage.mymodule.MyClass`, got {ref!r}"
        )
    module_s, cls_s = ref.rsplit(".", 1)
    module = importlib.import_module(module_s)
    return getattr(module, cls_s)
