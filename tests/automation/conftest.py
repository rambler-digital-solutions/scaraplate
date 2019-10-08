from pathlib import Path

import pytest


def convert_git_repo_to_bare(call_git, *, cwd: Path) -> None:
    """Git bare repo is a git repo without a working copy. `git clone`
    can clone these repos my simply pointing at their location in the local
    filesystem.
    """
    # https://stackoverflow.com/a/3251126
    call_git("git config --bool core.bare true", cwd=cwd)


@pytest.fixture
def template_bare_git_repo(tempdir_path, init_git_and_commit, call_git):
    template_path = tempdir_path / "remote_template"

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
git_remote_type: scaraplate.gitremotes.GitLab
default_strategy: scaraplate.strategies.Overwrite
strategies_mapping: {}
        """
    )
    init_git_and_commit(template_path, with_remote=False)
    call_git("git branch master2", cwd=template_path)

    convert_git_repo_to_bare(call_git, cwd=template_path)

    return template_path


@pytest.fixture
def project_bare_git_repo(tempdir_path, init_git_and_commit, call_git):
    target_project_path = tempdir_path / "remote_project"

    target_project_path.mkdir(parents=True)
    (target_project_path / "readme").write_text("hi")
    init_git_and_commit(target_project_path, with_remote=False)
    call_git("git branch master2", cwd=target_project_path)

    convert_git_repo_to_bare(call_git, cwd=target_project_path)

    return target_project_path
