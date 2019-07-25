import click

from scaraplate.rollup import rollup as _rollup


@click.group()
@click.version_option()
def main():
    pass


@main.command()
@click.argument("template_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("target_project_dir", type=click.Path(file_okay=False))
@click.option(
    "--no-input",
    is_flag=True,
    help=(
        "Do not prompt for missing data. Cookiecutter will use "
        "the defaults provided by the `cookiecutter.json` "
        "in the TEMPLATE_DIR."
    ),
)
def rollup(template_dir: str, target_project_dir: str, no_input: bool) -> None:
    """Rollup (apply) the cookiecutter template.

    The template from TEMPLATE_DIR is applied on top of TARGET_PROJECT_DIR.

    TEMPLATE_DIR must be a local path to the location of a git repo with
    the cookiecutter template to apply. It must contain `scaraplate.yaml`
    file in the root. The TEMPLATE_DIR must be in a git repo, because
    some strategies require the commit hash at HEAD and the git remote URL.

    TARGET_PROJECT_DIR should point to the directory where the template
    should be applied. Might not exist -- it will be created then.
    For monorepos this should point to the subproject inside the monorepo.
    """
    _rollup(
        template_dir=template_dir,
        target_project_dir=target_project_dir,
        no_input=no_input,
    )


if __name__ == "__main__":
    main(prog_name="scaraplate")  # pylint: disable=unexpected-keyword-arg
