import os
import subprocess
import tempfile
from pathlib import Path

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


@pytest.fixture
def call_git():
    def _call_git(shell_cmd: str, cwd: Path) -> str:
        env = {
            "USERNAME": "tests_scaraplate",
            "EMAIL": "pytest@scaraplate",
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
