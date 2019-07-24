import contextlib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import sentinel

import pytest

from scaraplate.config import ScaraplateYaml
from scaraplate.cookiecutter import ScaraplateConf
from scaraplate.rollup import (
    get_project_dest,
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


@pytest.mark.parametrize(
    "contents, expected_context",
    [
        (None, {}),
        ("", {}),
        (
            """
[cookiecutter_context]
metadata_author = Usermodel @ Rambler&Co
coverage_fail_under = 90
project_monorepo_name =
""",
            {
                "metadata_author": "Usermodel @ Rambler&Co",
                "coverage_fail_under": "90",
                "project_monorepo_name": "",
            },
        ),
    ],
)
def test_get_target_project_cookiecutter_context(
    tempdir_path: Path, contents: Optional[str], expected_context: Dict
) -> None:
    if contents is not None:
        (tempdir_path / ".scaraplate.conf").write_text(contents)

    scaraplate_yaml = ScaraplateYaml(
        default_strategy=sentinel.default,
        strategies_mapping={},
        git_remote_type=None,
        cookiecutter_context_type=ScaraplateConf,
    )

    assert expected_context == get_target_project_cookiecutter_context(
        tempdir_path, scaraplate_yaml
    )


def test_get_strategy():
    scaraplate_yaml = ScaraplateYaml(
        default_strategy=sentinel.default,
        strategies_mapping={
            "Jenkinsfile": sentinel.jenkinsfile,
            "some/nested/setup.py": sentinel.nested_setup_py,
            "src/*/__init__.py": sentinel.glob_init,
        },
        git_remote_type=None,
        cookiecutter_context_type=ScaraplateConf,
    )

    assert sentinel.default is get_strategy(scaraplate_yaml, Path("readme"))
    assert sentinel.jenkinsfile is get_strategy(scaraplate_yaml, Path("Jenkinsfile"))
    assert sentinel.nested_setup_py is get_strategy(
        scaraplate_yaml, Path("some/nested/setup.py")
    )
    assert sentinel.glob_init is get_strategy(
        scaraplate_yaml, Path("src/my_project/__init__.py")
    )
