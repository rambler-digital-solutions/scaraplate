import click


@click.group()
def main():
    pass


@main.command()
@click.argument("template_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("target_project_dir", type=click.Path(file_okay=False))
@click.option("--no-input", is_flag=True, help=("Do not prompt for missing data."))
def rollup(template_dir, target_project_dir, no_input):
    pass
