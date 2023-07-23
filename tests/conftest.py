import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def tempdir_path():
    with tempfile.TemporaryDirectory() as tempdir_path:
        yield Path(tempdir_path).resolve()


@pytest.fixture
def init_git_and_commit(call_git):
    def _init_git_and_commit(path: Path, with_remote=True) -> None:
        call_git("git init", cwd=path)
        call_git("git add --all .", cwd=path)
        call_git('git commit -m "initial"', cwd=path)
        if with_remote:
            call_git(
                "git remote add origin https://gitlab.localhost/nonexisting/repo.git",
                cwd=path,
            )

    return _init_git_and_commit


@pytest.fixture(scope="session", autouse=True)
def mock_git_env():
    os.environ.pop("SSH_AUTH_SOCK", None)
    with patch.dict(
        os.environ,
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "",
            "GIT_CONFIG_SYSTEM": "",
        },
    ):
        yield


@pytest.fixture
def call_git():
    def _call_git(shell_cmd: str, cwd: Path) -> str:
        env = {
            "GIT_AUTHOR_EMAIL": "pytest@scaraplate",
            "GIT_AUTHOR_NAME": "tests_scaraplate",
            "GIT_COMMITTER_EMAIL": "pytest@scaraplate",
            "GIT_COMMITTER_NAME": "tests_scaraplate",
            "PATH": os.getenv("PATH", os.defpath),
        }
        out = subprocess.run(
            shell_cmd,
            shell=True,
            check=True,
            cwd=cwd,
            env=env,
            timeout=5,
            stdout=subprocess.PIPE,
        )
        stdout = out.stdout.decode().strip()
        print(stdout)
        return stdout

    return _call_git
