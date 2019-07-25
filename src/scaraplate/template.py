import subprocess
from pathlib import Path
from typing import NamedTuple, Optional, Sequence, Type

from scaraplate.gitremotes import GitRemote, make_git_remote


class TemplateMeta(NamedTuple):
    """Metadata of the template's git repo status."""

    git_project_url: str
    commit_hash: str
    commit_url: str
    is_git_dirty: bool


def get_template_meta_from_git(
    template_path: Path, *, git_remote_type: Optional[Type[GitRemote]] = None
) -> TemplateMeta:
    remote_url = _git_remote_origin(template_path)
    commit_hash = _git_head_commit_hash(template_path)

    git_remote = make_git_remote(remote_url, git_remote_type=git_remote_type)

    return TemplateMeta(
        git_project_url=git_remote.project_url(),
        commit_hash=commit_hash,
        commit_url=git_remote.commit_url(commit_hash),
        is_git_dirty=_is_git_dirty(template_path),
    )


def _git_head_commit_hash(cwd: Path) -> str:
    return _call_git(["git", "rev-parse", "--verify", "HEAD"], cwd)


def _is_git_dirty(cwd: Path) -> bool:
    return bool(_call_git(["git", "status", "--porcelain"], cwd))


def _git_remote_origin(cwd: Path) -> str:
    # Would raise if there's no remote called `origin`.
    return _call_git(["git", "config", "--get", "remote.origin.url"], cwd)


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
