from click.testing import CliRunner

from scaraplate.__main__ import main


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0


def test_rollup_help():
    runner = CliRunner()
    result = runner.invoke(main, ["rollup", "--help"])
    assert result.exit_code == 0
