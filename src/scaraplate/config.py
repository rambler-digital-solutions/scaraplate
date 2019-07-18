import importlib
from pathlib import Path
from typing import Dict, Mapping, NamedTuple, Type

import yaml

from .strategies import Strategy


class ScaraplateYaml(NamedTuple):
    default_strategy: Type[Strategy]
    strategies_mapping: Mapping[str, Type[Strategy]]


def get_scaraplate_yaml(template_path: Path) -> ScaraplateYaml:
    config = yaml.safe_load((template_path / "scaraplate.yaml").read_text())
    default_strategy = class_from_str(config["default_strategy"])
    if not issubclass(default_strategy, Strategy) or default_strategy == Strategy:
        raise RuntimeError(
            f"`{default_strategy}` is not a subclass of "
            f"`scaraplate.strategies.Strategy`"
        )

    strategies_mapping: Dict[str, Type[Strategy]] = {  # type: ignore
        str(path): class_from_str(ref)
        for path, ref in config["strategies_mapping"].items()
    }
    for cls in strategies_mapping.values():
        if not issubclass(cls, Strategy) or default_strategy == Strategy:
            raise RuntimeError(
                f"`{default_strategy}` is not a subclass of "
                f"`scaraplate.strategies.Strategy`"
            )
    return ScaraplateYaml(
        default_strategy=default_strategy, strategies_mapping=strategies_mapping
    )


def class_from_str(ref: str) -> Type[object]:
    module_s, cls_s = ref.rsplit(".", 1)
    module = importlib.import_module(module_s)
    return getattr(module, cls_s)
