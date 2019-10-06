import collections
from typing import Mapping

import click

from scaraplate.rollup import rollup as _rollup


def validate_extra_context(ctx, param, value):
    """Validate extra context."""
    # vendored from https://github.com/cookiecutter/cookiecutter/blob/673f773bfaf591b056d977c4ab82b45d90dce11e/cookiecutter/cli.py#L35-L46  # noqa
    for s in value:
        if "=" not in s:
            raise click.BadParameter(
                "EXTRA_CONTEXT should contain items of the form key=value; "
                "'{}' doesn't match that form".format(s)
            )

    # Convert tuple -- e.g.: (u'program_name=foobar', u'startsecs=66')
    # to dict -- e.g.: {'program_name': 'foobar', 'startsecs': '66'}
    return collections.OrderedDict(s.split("=", 1) for s in value) or None


@click.group()
@click.version_option()
def main():
    pass


@main.command()
@click.argument("template_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("target_project_dir", type=click.Path(file_okay=False))
@click.argument("extra_context", nargs=-1, callback=validate_extra_context)
@click.option(
    "--no-input",
    is_flag=True,
    help=(
        "Do not prompt for missing data. Cookiecutter will use "
        "the defaults provided by the `cookiecutter.json` "
        "in the TEMPLATE_DIR."
    ),
)
def rollup(
    *,
    template_dir: str,
    target_project_dir: str,
    no_input: bool,
    extra_context: Mapping[str, str],
) -> None:
    """Rollup (apply) the cookiecutter template.

    The template from TEMPLATE_DIR is applied on top of TARGET_PROJECT_DIR.

    TEMPLATE_DIR must be a local path to the location of a git repo with
    the cookiecutter template to apply. It must contain `scaraplate.yaml`
    file in the root. The TEMPLATE_DIR must be in a git repo, because
    some strategies require the commit hash at HEAD and the git remote URL.

    TARGET_PROJECT_DIR should point to the directory where the template
    should be applied. Might not exist -- it will be created then.
    For monorepos this should point to the subproject inside the monorepo.

    EXTRA_CONTEXT is a list of `key=value` pairs, just like in
    `cookiecutter` command.
    """
    _rollup(
        template_dir=template_dir,
        target_project_dir=target_project_dir,
        no_input=no_input,
        extra_context=extra_context,
    )


if __name__ == "__main__":
    main(prog_name="scaraplate")  # pylint: disable=unexpected-keyword-arg
