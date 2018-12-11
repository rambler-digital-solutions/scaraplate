import re
import subprocess
from pathlib import Path
from typing import NamedTuple, Sequence


class TemplateMeta(NamedTuple):
    gitlab_project_url: str
    commit_hash: str
    commit_url: str
    is_git_dirty: bool


def get_template_meta_from_git(template_path: Path) -> TemplateMeta:
    gitlab_project_url = _gitlab_url_from_remote(_git_remote_origin(template_path))
    commit_hash = _git_head_commit_hash(template_path)

    return TemplateMeta(
        gitlab_project_url=gitlab_project_url,
        commit_hash=commit_hash,
        commit_url=_gitlab_commit_url(gitlab_project_url, commit_hash),
        is_git_dirty=_is_git_dirty(template_path),
    )


def _gitlab_commit_url(project_url: str, commit_hash: str) -> str:
    return f"{project_url.rstrip('/')}/commit/{commit_hash}"


def _git_head_commit_hash(cwd: Path) -> str:
    return _call_git(["git", "rev-parse", "--verify", "HEAD"], cwd)


def _is_git_dirty(cwd: Path) -> bool:
    return bool(_call_git(["git", "status", "--porcelain"], cwd))


def _git_remote_origin(cwd: Path) -> str:
    # Would raise if there's no remote called `origin`.
    return _call_git(["git", "config", "--get", "remote.origin.url"], cwd)


def _gitlab_url_from_remote(remote_url: str) -> str:
    url = remote_url
    # `git@gitlab.com:<suffix>` -> `https://gitlab.com/<suffix>`
    url = re.sub(r"^[^@]*@([^:]+):", r"https://\1/", url)
    url = re.sub(r".git$", "", url)
    return url


def _call_git(command: Sequence[str], cwd: Path) -> str:
    try:
        out = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, check=True)
    except Exception:
        raise RuntimeError(
            f"{command} command failed in the template "
            f"'{cwd}'. "
            f"Ensure that it is a valid git repo."
        )
    else:
        return out.stdout.decode().strip()
