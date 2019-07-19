import io
from typing import BinaryIO, Optional, Type

import pytest
import yaml

from scaraplate import strategies
from scaraplate.template import TemplateMeta


def pytest_collect_file(parent, path):
    # https://docs.pytest.org/en/latest/example/nonpython.html
    if path.ext == ".yml" and path.basename.startswith("test"):
        return YamlFile(path, parent)


class YamlFile(pytest.File):
    def collect(self):
        spec = yaml.safe_load(self.fspath.open())
        strategy = spec["strategy"]
        testcases = spec["testcases"]

        for testcase in testcases:
            yield YamlItem(testcase["name"], self, strategy, testcase)


class YamlItem(pytest.Item):
    def __init__(self, name, parent, strategy, testcase):
        super().__init__(name, parent)
        self.strategy = strategy
        self.testcase = testcase

    def runtest(self):
        strategy_type = getattr(strategies, self.strategy)
        run_strategy_test(
            strategy_type=strategy_type,
            template=self.testcase["template"],
            target=self.testcase["target"],
            is_git_dirty=self.testcase["is_git_dirty"],
            out=self.testcase["out"],
        )

    def reportinfo(self):
        return self.fspath, 0, f"name: {self.name}"


def run_strategy_test(
    strategy_type: Type[strategies.Strategy],
    template: str,
    target: Optional[str],
    is_git_dirty: bool,
    out: str,
):
    if target is not None:
        target_contents: Optional[BinaryIO] = io.BytesIO(target.encode())
    else:
        target_contents = None

    template_contents = io.BytesIO(template.encode())

    strategy = strategy_type(
        target_contents=target_contents,
        template_contents=template_contents,
        template_meta=TemplateMeta(
            git_project_url="https://github.com/rambler-digital-solutions/scaraplate-example-template",
            commit_hash="1111111111111111111111111111111111111111",
            commit_url=(
                "https://github.com/rambler-digital-solutions/scaraplate-example-template"
                "/commit/1111111111111111111111111111111111111111"
            ),
            is_git_dirty=is_git_dirty,
        ),
        config={},
    )

    assert out == strategy.apply().read().decode()
