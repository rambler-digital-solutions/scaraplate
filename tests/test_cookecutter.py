from contextlib import ExitStack
from pathlib import Path

import pytest

from scaraplate.cookiecutter import ScaraplateConf, SetupCfg


@pytest.mark.parametrize(
    "contents, expected_context",
    [
        (None, None),
        ("", {}),
        (
            """
[metadata]
name = holywarrior
""",
            {},
        ),
        (
            """
[tool:cookiecutter_context]
""",
            {},
        ),
        (
            """
[metadata]
name = holywarrior


[tool:cookiecutter_context]
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
def test_setupcfg(tempdir_path: Path, contents, expected_context):
    if contents is not None:
        (tempdir_path / "setup.cfg").write_text(contents)

    with ExitStack() as stack:
        if expected_context is None:
            stack.enter_context(pytest.raises(FileNotFoundError))

        cookiecutter_context = SetupCfg(tempdir_path)
        assert expected_context == cookiecutter_context.read()


@pytest.mark.parametrize(
    "contents, expected_context",
    [
        (None, None),
        ("", {}),
        (
            """
[foreignsection]
name = holywarrior
""",
            {},
        ),
        (
            """
[cookiecutter_context]
""",
            {},
        ),
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
def test_scaraplate_conf(tempdir_path: Path, contents, expected_context):
    if contents is not None:
        (tempdir_path / ".scaraplate.conf").write_text(contents)

    with ExitStack() as stack:
        if expected_context is None:
            stack.enter_context(pytest.raises(FileNotFoundError))

        cookiecutter_context = ScaraplateConf(tempdir_path)
        assert expected_context == cookiecutter_context.read()
