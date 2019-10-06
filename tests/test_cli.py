from unittest.mock import patch

from click.testing import CliRunner

import scaraplate.__main__ as main_module
from scaraplate.__main__ import main


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output


def test_rollup_help():
    runner = CliRunner()
    result = runner.invoke(main, ["rollup", "--help"])
    assert result.exit_code == 0, result.output


def test_extra_context():
    with patch.object(main_module, "_rollup") as mock_rollup:
        runner = CliRunner()
        result = runner.invoke(
            main, ["rollup", ".", "mydest", "key1=value1", "key2=value2"]
        )
        assert result.exit_code == 0, result.output

        assert mock_rollup.call_count == 1
        _, kwargs = mock_rollup.call_args
        assert kwargs["extra_context"] == {"key1": "value1", "key2": "value2"}


def test_extra_context_incorrect():
    with patch.object(main_module, "_rollup"):
        runner = CliRunner()
        result = runner.invoke(main, ["rollup", ".", "mydest", "key1value1"])
        assert result.exit_code == 2, result.output
        assert (
            "EXTRA_CONTEXT should contain items of the form key=value" in result.output
        )
