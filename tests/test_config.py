from pathlib import Path

import jinja2.exceptions
import pytest

import scaraplate.strategies
from scaraplate.config import (
    ScaraplateYamlOptions,
    ScaraplateYamlStrategies,
    StrategyNode,
    get_scaraplate_yaml_options,
    get_scaraplate_yaml_strategies,
)
from scaraplate.cookiecutter import CookieCutterContextDict, ScaraplateConf, SetupCfg
from scaraplate.gitremotes import GitHub


@pytest.mark.parametrize(
    "yaml_text, expected",
    [
        (
            """
git_remote_type: scaraplate.gitremotes.GitHub
""",
            ScaraplateYamlOptions(
                git_remote_type=GitHub, cookiecutter_context_type=ScaraplateConf
            ),
        ),
        (
            """
cookiecutter_context_type: scaraplate.cookiecutter.SetupCfg
""",
            ScaraplateYamlOptions(
                git_remote_type=None, cookiecutter_context_type=SetupCfg
            ),
        ),
    ],
)
def test_get_scaraplate_yaml_options_valid(
    tempdir_path: Path, yaml_text, expected
) -> None:
    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    scaraplate_yaml_options = get_scaraplate_yaml_options(tempdir_path)
    assert scaraplate_yaml_options == expected


@pytest.mark.parametrize(
    "yaml_text, cookiecutter_context_dict, expected",
    [
        # Basic syntax:
        (
            """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping:
  Jenkinsfile: scaraplate.strategies.TemplateHash
  'some/nested/setup.py': scaraplate.strategies.TemplateHash
""",
            {},
            ScaraplateYamlStrategies(
                default_strategy=StrategyNode(
                    strategy=scaraplate.strategies.Overwrite, config={}
                ),
                strategies_mapping={
                    "Jenkinsfile": StrategyNode(
                        strategy=scaraplate.strategies.TemplateHash, config={}
                    ),
                    "some/nested/setup.py": StrategyNode(
                        strategy=scaraplate.strategies.TemplateHash, config={}
                    ),
                },
            ),
        ),
        # Extended syntax (with config):
        (
            """
default_strategy:
  strategy: scaraplate.strategies.Overwrite
  config:
    some_key: True
strategies_mapping:
  other_file.txt:
    strategy: scaraplate.strategies.IfMissing
    unrelated_key_but_okay: 1
  another_file.txt:
    strategy: scaraplate.strategies.SortedUniqueLines
    config:
      some_key: True
""",
            {},
            ScaraplateYamlStrategies(
                default_strategy=StrategyNode(
                    strategy=scaraplate.strategies.Overwrite, config={"some_key": True}
                ),
                strategies_mapping={
                    "other_file.txt": StrategyNode(
                        strategy=scaraplate.strategies.IfMissing, config={}
                    ),
                    "another_file.txt": StrategyNode(
                        strategy=scaraplate.strategies.SortedUniqueLines,
                        config={"some_key": True},
                    ),
                },
            ),
        ),
        # Jinja2 filenames and globs:
        (
            """
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping:
  '*.txt': scaraplate.strategies.IfMissing
  'src/{{ cookiecutter.file1 }}': scaraplate.strategies.TemplateHash
  'src/{{ cookiecutter.file2 }}': scaraplate.strategies.IfMissing
""",
            {"file1": "zzz.py", "file2": "aaa.py"},
            ScaraplateYamlStrategies(
                default_strategy=StrategyNode(
                    strategy=scaraplate.strategies.Overwrite, config={}
                ),
                strategies_mapping={
                    "*.txt": StrategyNode(
                        strategy=scaraplate.strategies.IfMissing, config={}
                    ),
                    "src/aaa.py": StrategyNode(
                        strategy=scaraplate.strategies.IfMissing, config={}
                    ),
                    "src/zzz.py": StrategyNode(
                        strategy=scaraplate.strategies.TemplateHash, config={}
                    ),
                },
            ),
        ),
    ],
)
def test_get_scaraplate_yaml_strategies_valid(
    tempdir_path: Path, yaml_text, cookiecutter_context_dict, expected
) -> None:
    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    scaraplate_yaml_strategies = get_scaraplate_yaml_strategies(
        tempdir_path, cookiecutter_context_dict
    )
    assert scaraplate_yaml_strategies == expected


@pytest.mark.parametrize(
    "cls",
    [
        "tempfile.TemporaryDirectory",
        "tempfile",
        "scaraplate.strategies.Strategy",
        '{"strategy": "tempfile.TemporaryDirectory"}',
        '{"strategy": 42}',
        '{"config": {}}',  # strategy is missing
        '{"strategy": "scaraplate.strategies.Overwrite", "config": 42}',
        "42",
    ],
)
@pytest.mark.parametrize("mutation_target", ["default_strategy", "strategies_mapping"])
def test_get_scaraplate_yaml_strategies_invalid(
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
    with pytest.raises(ValueError):
        get_scaraplate_yaml_strategies(tempdir_path, CookieCutterContextDict({}))


@pytest.mark.parametrize(
    "key, cookiecutter_context_dict",
    [
        ("'{{ cookiecutter.missingkey }}'", {"anotherkey": "42"}),
        ("'{{ somevar }}'", {"somavar": "42"}),  # doesn't start with `cookiecutter.`
    ],
)
def test_get_scaraplate_yaml_strategies_invalid_keys(
    tempdir_path: Path, key, cookiecutter_context_dict
) -> None:
    yaml_text = f"""
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping:
  {key}: scaraplate.strategies.Overwrite
"""
    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    with pytest.raises(jinja2.exceptions.UndefinedError):
        get_scaraplate_yaml_strategies(tempdir_path, cookiecutter_context_dict)


@pytest.mark.parametrize(
    "cls",
    [
        "tempfile.TemporaryDirectory",
        "tempfile",
        "scaraplate.gitremotes.GitRemote",
        "scaraplate.cookiecutter.ScaraplateConf",
        '{"strategy": "scaraplate.gitremotes.GitLab"}',
        "42",
    ],
)
def test_get_scaraplate_yaml_options_invalid_git_remotes(
    tempdir_path: Path, cls: str
) -> None:
    yaml_text = f"""
git_remote_type: {cls}
"""
    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    with pytest.raises(ValueError):
        get_scaraplate_yaml_options(tempdir_path)


@pytest.mark.parametrize(
    "cls",
    [
        "tempfile.TemporaryDirectory",
        "tempfile",
        "scaraplate.gitremotes.GitHub",
        "scaraplate.cookiecutter.CookieCutterContext",
        '{"strategy": "scaraplate.cookiecutter.ScaraplateConf"}',
        "42",
    ],
)
def test_get_scaraplate_yaml_options_invalid_cookiecutter_context(
    tempdir_path: Path, cls: str
) -> None:
    yaml_text = f"""
cookiecutter_context_type: {cls}
"""
    (tempdir_path / "scaraplate.yaml").write_text(yaml_text)
    with pytest.raises(ValueError):
        get_scaraplate_yaml_options(tempdir_path)
