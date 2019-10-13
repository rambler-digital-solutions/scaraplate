import contextlib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import sentinel

import pytest

from scaraplate.config import ScaraplateYamlOptions, ScaraplateYamlStrategies
from scaraplate.cookiecutter import ScaraplateConf
from scaraplate.rollup import (
    InvalidScaraplateTemplateError,
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
    (cookiecutter_path / ".scaraplate.conf").write_text(
        """[cookiecutter_context]
{%- for key, value in cookiecutter.items()|sort %}
{{ key }} = {{ value }}
{%- endfor %}
"""
    )
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


def test_add_remove_template_var(tempdir_path, init_git_and_commit):
    template_path = tempdir_path / "template"
    target_project_path = tempdir_path / "test"

    # Prepare template
    cookiecutter_path = template_path / "{{cookiecutter.project_dest}}"
    cookiecutter_path.mkdir(parents=True)
    (cookiecutter_path / ".scaraplate.conf").write_text(
        """[cookiecutter_context]
{%- for key, value in cookiecutter.items()|sort %}
{{ key }} = {{ value }}
{%- endfor %}
"""
    )
    (template_path / "cookiecutter.json").write_text(
        '{"project_dest": "test", "removed_var": 42}'
    )
    (template_path / "scaraplate.yaml").write_text(
        """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping: {}
        """
    )
    init_git_and_commit(template_path)

    rollup(
        template_dir=str(template_path),
        target_project_dir=str(target_project_path),
        no_input=True,
    )
    assert (target_project_path / ".scaraplate.conf").read_text() == (
        """[cookiecutter_context]
_template = template
project_dest = test
removed_var = 42
"""
    )

    # Remove `removed_var` and add `added_var`
    (template_path / "cookiecutter.json").write_text(
        '{"project_dest": "test", "added_var": 24}'
    )
    rollup(
        template_dir=str(template_path),
        target_project_dir=str(target_project_path),
        no_input=True,
    )
    assert (target_project_path / ".scaraplate.conf").read_text() == (
        """[cookiecutter_context]
_template = template
added_var = 24
project_dest = test
"""
    )


@pytest.mark.parametrize("create_empty", [False, True])
def test_invalid_template_is_raised_for_missing_cookiecutter_context(
    create_empty, tempdir_path, init_git_and_commit
):
    template_path = tempdir_path / "template"
    target_project_path = tempdir_path / "test"

    # Prepare template
    cookiecutter_path = template_path / "{{cookiecutter.project_dest}}"
    cookiecutter_path.mkdir(parents=True)
    if create_empty:
        (cookiecutter_path / ".scaraplate.conf").write_text("")
    (template_path / "cookiecutter.json").write_text('{"project_dest": "test"}')
    (template_path / "scaraplate.yaml").write_text(
        """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping: {}
        """
    )
    init_git_and_commit(template_path)

    with pytest.raises(InvalidScaraplateTemplateError) as excinfo:
        rollup(
            template_dir=str(template_path),
            target_project_dir=str(target_project_path),
            no_input=True,
        )
    assert "cookiecutter context file `.scaraplate.conf` " in str(excinfo.value)


def test_extra_context(tempdir_path, init_git_and_commit):
    template_path = tempdir_path / "template"
    target_project_path = tempdir_path / "test"

    # Prepare template
    cookiecutter_path = template_path / "{{cookiecutter.project_dest}}"
    cookiecutter_path.mkdir(parents=True)
    (cookiecutter_path / "sense_vars").write_text("{{ cookiecutter|jsonify }}\n")
    (cookiecutter_path / ".scaraplate.conf").write_text(
        """[cookiecutter_context]
{%- for key, value in cookiecutter.items()|sort %}
{{ key }} = {{ value }}
{%- endfor %}
"""
    )
    (template_path / "cookiecutter.json").write_text(
        '{"project_dest": "test", "key1": null, "key2": null}'
    )
    (template_path / "scaraplate.yaml").write_text(
        """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping: {}
        """
    )
    init_git_and_commit(template_path)

    # Initial rollup
    rollup(
        template_dir=str(template_path),
        target_project_dir=str(target_project_path),
        no_input=True,
        extra_context={"key1": "initial1", "key2": "initial2"},
    )
    with open((target_project_path / "sense_vars"), "rt") as f:
        assert json.load(f) == {
            "_template": "template",
            "project_dest": "test",
            "key1": "initial1",
            "key2": "initial2",
        }

    # A second rollup with a different context
    rollup(
        template_dir=str(template_path),
        target_project_dir=str(target_project_path),
        no_input=True,
        extra_context={"key1": "second1", "key2": "second2"},
    )
    with open((target_project_path / "sense_vars"), "rt") as f:
        assert json.load(f) == {
            "_template": "template",
            "project_dest": "test",
            "key1": "second1",
            "key2": "second2",
        }


def test_rollup_with_jinja2_mapping(tempdir_path, init_git_and_commit):
    template_path = tempdir_path / "template"
    target_project_path = tempdir_path / "test"

    # Prepare template
    cookiecutter_path = template_path / "{{cookiecutter.project_dest}}"
    cookiecutter_path.mkdir(parents=True)
    (cookiecutter_path / "sense_vars").write_text("{{ cookiecutter|jsonify }}\n")
    (cookiecutter_path / ".scaraplate.conf").write_text(
        """[cookiecutter_context]
{%- for key, value in cookiecutter.items()|sort %}
{{ key }} = {{ value }}
{%- endfor %}
"""
    )
    (template_path / "cookiecutter.json").write_text(
        '{"project_dest": "test", "file1": null, "file2": "boop"}'
    )
    (template_path / "scaraplate.yaml").write_text(
        """
default_strategy: scaraplate.strategies.SortedUniqueLines
strategies_mapping:
  '{{ cookiecutter.file1 }}.txt': scaraplate.strategies.IfMissing
  '{{ cookiecutter.file2 }}.txt': scaraplate.strategies.Overwrite
        """
    )
    (cookiecutter_path / "{{ cookiecutter.file1 }}.txt").write_text("template!")
    (cookiecutter_path / "{{ cookiecutter.file2 }}.txt").write_text("template!")
    init_git_and_commit(template_path)

    # Initial rollup
    rollup(
        template_dir=str(template_path),
        target_project_dir=str(target_project_path),
        no_input=True,
        extra_context={"file1": "beep"},
    )
    assert "template!" == (target_project_path / "beep.txt").read_text()
    assert "template!" == (target_project_path / "boop.txt").read_text()
    (target_project_path / "beep.txt").write_text("target!")
    (target_project_path / "boop.txt").write_text("target!")

    # A second rollup (beep.txt should not be changed)
    rollup(
        template_dir=str(template_path),
        target_project_dir=str(target_project_path),
        no_input=True,
        extra_context={"file1": "beep"},
    )
    assert "target!" == (target_project_path / "beep.txt").read_text()
    assert "template!" == (target_project_path / "boop.txt").read_text()


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

    scaraplate_yaml_options = ScaraplateYamlOptions(
        git_remote_type=None, cookiecutter_context_type=ScaraplateConf
    )

    assert expected_context == get_target_project_cookiecutter_context(
        tempdir_path, scaraplate_yaml_options
    )


def test_get_strategy():
    scaraplate_yaml_strategies = ScaraplateYamlStrategies(
        default_strategy=sentinel.default,
        strategies_mapping={
            "Jenkinsfile": sentinel.jenkinsfile,
            "some/nested/setup.py": sentinel.nested_setup_py,
            "src/*/__init__.py": sentinel.glob_init,
        },
    )

    assert sentinel.default is get_strategy(scaraplate_yaml_strategies, Path("readme"))
    assert sentinel.jenkinsfile is get_strategy(
        scaraplate_yaml_strategies, Path("Jenkinsfile")
    )
    assert sentinel.nested_setup_py is get_strategy(
        scaraplate_yaml_strategies, Path("some/nested/setup.py")
    )
    assert sentinel.glob_init is get_strategy(
        scaraplate_yaml_strategies, Path("src/my_project/__init__.py")
    )
