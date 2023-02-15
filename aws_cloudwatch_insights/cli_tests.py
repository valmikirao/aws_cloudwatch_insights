import re

from click.testing import CliRunner

from aws_cloudwatch_insights import cli


def test_command_line_interface():
    """
    Test the CLI.
    To-Do: Add more interesting cli test than this
    """
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 1, 'Fails with no arguments'
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert re.search(r'--help\s+Show this message and exit\.', help_result.output)
