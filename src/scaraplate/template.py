import os
import subprocess
from pathlib import Path
from typing import Dict, NamedTuple, Optional, Sequence, Type

from scaraplate.gitremotes import GitRemote, make_git_remote


class TemplateMeta(NamedTuple):
    """Metadata of the template's git repo status."""

    git_project_url: str
    commit_hash: str
    commit_url: str
    is_git_dirty: bool
    head_ref: Optional[str]


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
        head_ref=_git_resolve_head(template_path),
    )


def _git_head_commit_hash(cwd: Path) -> str:
    return _call_git(["rev-parse", "--verify", "HEAD"], cwd)


def _is_git_dirty(cwd: Path) -> bool:
    return bool(_call_git(["status", "--porcelain"], cwd))


def _git_resolve_head(cwd: Path) -> Optional[str]:
    ref = _call_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if ref == "HEAD":
        # Detached HEAD (some specific commit has been checked out).
        return None
    return ref


def _git_remote_origin(cwd: Path) -> str:
    # Would raise if there's no remote called `origin`.
    return _call_git(["config", "--get", "remote.origin.url"], cwd)


def _call_git(
    command: Sequence[str], cwd: Path, *, env: Optional[Dict[str, str]] = None
) -> str:
    env_combined = dict(os.environ)
    if env:
        env_combined.update(env)

    try:
        out = subprocess.run(
            ["git", *command],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            env=env_combined,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"{command} command failed in the directory "
            f"'{cwd}'. "
            f"Ensure that it is a valid git repo."
            f"\n"
            f"stdout:\n"
            f"{e.stdout.decode()}\n"
            f"stderr:\n"
            f"{e.stderr.decode()}\n"
        )
    else:
        return out.stdout.decode().strip()
