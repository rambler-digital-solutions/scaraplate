from pathlib import Path

import pytest

import scaraplate.strategies
from scaraplate.config import ScaraplateYaml, get_scaraplate_yaml


def test_get_scaraplate_yaml_valid(tempdir_path: Path) -> None:
    yaml_text = """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping:
  Jenkinsfile: scaraplate.strategies.TemplateHash
  'some/nested/setup.py': scaraplate.strategies.TemplateHash
"""
    expected = ScaraplateYaml(
        default_strategy=scaraplate.strategies.Overwrite,
        strategies_mapping={
            "Jenkinsfile": scaraplate.strategies.TemplateHash,
            "some/nested/setup.py": scaraplate.strategies.TemplateHash,
        },
    )

    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    scaraplate_yaml = get_scaraplate_yaml(tempdir_path)
    assert scaraplate_yaml == expected


@pytest.mark.parametrize("cls", ["tempfile.TemporaryDirectory", "tempfile"])
@pytest.mark.parametrize("mutation_target", ["default_strategy", "strategies_mapping"])
def test_get_scaraplate_yaml_invalid(
    tempdir_path: Path, cls: str, mutation_target: str
) -> None:
    classes = dict(
        default_strategy="scaraplate.strategies.Overwrite",
        strategies_mapping="scaraplate.strategies.Overwrite",
    )
    classes[mutation_target] = cls

    yaml_text = f"""
default_strategy: {classes['default_strategy']}
strategies_mapping:
  Jenkinsfile: {classes['strategies_mapping']}
"""
    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    with pytest.raises((RuntimeError, ValueError)):
        get_scaraplate_yaml(tempdir_path)
