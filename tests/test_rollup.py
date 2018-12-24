import contextlib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import sentinel

import pytest

import scaraplate.strategies
from scaraplate.rollup import (
    ScaraplateYaml,
    get_project_dest,
    get_scaraplate_yaml,
    get_strategy,
    get_target_project_cookiecutter_context,
    get_template_root_and_dir,
    rollup,
)


@contextlib.contextmanager
def with_working_directory(target_dir: Path):
    cur = os.getcwd()
    os.chdir(target_dir)
    try:
        yield
    finally:
        os.chdir(cur)


@pytest.mark.parametrize("apply_count", [1, 2])
def test_rollup_fuzzy(tempdir_path, apply_count, init_git_and_commit):
    template_path = tempdir_path / "template"
    target_project_path = tempdir_path / "test"

    # Prepare template
    cookiecutter_path = template_path / "{{cookiecutter.project_dest}}"
    cookiecutter_path.mkdir(parents=True)
    (cookiecutter_path / "README.md").write_text(
        "{{ cookiecutter.project_dest }} mock!"
    )
    (cookiecutter_path / "setup.py").write_text("#!/usr/bin/env python\n")
    (cookiecutter_path / "setup.py").chmod(0o755)
    (cookiecutter_path / "sense_vars").write_text("{{ cookiecutter|jsonify }}\n")
    (template_path / "cookiecutter.json").write_text('{"project_dest": "test"}')
    (template_path / "scaraplate.yaml").write_text(
        """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping:
  setup.py: scaraplate.strategies.TemplateHash
        """
    )
    init_git_and_commit(template_path)

    # Apply template (possibly multiple times)
    for i in range(apply_count):
        rollup(
            template_dir=str(template_path),
            target_project_dir=str(target_project_path),
            no_input=True,
        )

        assert "test mock!" == (target_project_path / "README.md").read_text()
        assert 0o755 == (0o777 & (target_project_path / "setup.py").stat().st_mode)

        with open((target_project_path / "sense_vars"), "rt") as f:
            assert json.load(f) == {
                # fmt: off
                "_template": "template",
                "project_dest": "test",
                # fmt: on
            }


def test_get_project_dest(tempdir_path: Path) -> None:
    target = tempdir_path / "myproject"
    with with_working_directory(tempdir_path):
        assert "myproject" == get_project_dest(Path("myproject"))

    target.mkdir()
    with with_working_directory(target):
        assert "myproject" == get_project_dest(Path("."))


def test_get_template_root_and_dir(tempdir_path: Path) -> None:
    target = tempdir_path / "myproject"
    target.mkdir()

    with with_working_directory(tempdir_path):
        assert (tempdir_path, "myproject") == get_template_root_and_dir(
            Path("myproject")
        )
        assert (tempdir_path, "myproject") == get_template_root_and_dir(
            tempdir_path / "myproject"
        )

    with with_working_directory(target):
        assert (tempdir_path, "myproject") == get_template_root_and_dir(Path("."))


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


setup_cfg_without_context = """
[metadata]
name = holywarrior
"""

setup_cfg_with_context = """
[metadata]
name = holywarrior


[tool:cookiecutter_context]
metadata_author = Usermodel @ Rambler&Co
coverage_fail_under = 90
project_monorepo_name =
"""


@pytest.mark.parametrize(
    "setup_cfg_text, expected_context",
    [
        (None, {}),
        (setup_cfg_without_context, {}),
        (
            setup_cfg_with_context,
            {
                "metadata_author": "Usermodel @ Rambler&Co",
                "coverage_fail_under": "90",
                "project_monorepo_name": "",
            },
        ),
    ],
)
def test_get_target_project_cookiecutter_context(
    tempdir_path: Path, setup_cfg_text: Optional[str], expected_context: Dict
) -> None:
    if setup_cfg_text is not None:
        (tempdir_path / "setup.cfg").write_text(setup_cfg_text)

    assert expected_context == get_target_project_cookiecutter_context(tempdir_path)


def test_get_strategy():
    scaraplate_yaml = ScaraplateYaml(
        default_strategy=sentinel.default,
        strategies_mapping={
            "Jenkinsfile": sentinel.jenkinsfile,
            "some/nested/setup.py": sentinel.nested_setup_py,
            "src/*/__init__.py": sentinel.glob_init,
        },
    )

    assert sentinel.default is get_strategy(scaraplate_yaml, Path("readme"))
    assert sentinel.jenkinsfile is get_strategy(scaraplate_yaml, Path("Jenkinsfile"))
    assert sentinel.nested_setup_py is get_strategy(
        scaraplate_yaml, Path("some/nested/setup.py")
    )
    assert sentinel.glob_init is get_strategy(
        scaraplate_yaml, Path("src/my_project/__init__.py")
    )
