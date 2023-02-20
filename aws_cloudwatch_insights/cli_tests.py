import re

import pytest

cli_modules_loaded = False

try:
    from click.testing import CliRunner
    from aws_cloudwatch_insights import cli
    cli_modules_loaded = True
except ModuleNotFoundError:
    # none of the tests here should be run if this fails
    pass


@pytest.mark.cli
def test_cli_modules_loaded():
    assert cli_modules_loaded, 'Tests in this file only work if you\'ve installed the full packaged' \
                               ' (ie run `pip install -e \'.[all]\'`)'


@pytest.mark.cli
def test_command_line_interface():
    """
    Test the CLI.
    To-Do: Add more interesting cli test than this
    """
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 2, 'Fails with no arguments'
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert re.search(r'--help\s+Show this message and exit\.', help_result.output)
