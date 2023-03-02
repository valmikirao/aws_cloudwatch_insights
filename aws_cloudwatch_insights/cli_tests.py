import os.path
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import create_autospec, call, ANY

import pytest
from freezegun import freeze_time

cli_modules_loaded = False

try:
    from click.testing import CliRunner
    from aws_cloudwatch_insights import cli
    cli_modules_loaded = True
except ModuleNotFoundError:
    # none of the tests here should be run if this fails
    pass

PROJECT_ROOT = os.path.split(
    os.path.split(__file__)[0]
)[0]

NOW = datetime(2001, 1, 1, tzinfo=timezone.utc)
QUERY = """fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 20"""
QUERY_YAML = """fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 30"""


@pytest.mark.cli
def test_cli_modules_loaded():
    assert cli_modules_loaded, 'Tests in this file only work if you\'ve installed the full packaged' \
                               ' (ie run `pip install -e \'.[cli]\'`)'


@pytest.mark.cli
def test_command_line_interface_basic():
    """
    Test the CLI just plain works
    """
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 2, 'Fails with no arguments'
    help_result = runner.invoke(cli.main, ['--help'])
    assert help_result.exit_code == 0
    assert re.search(r'--help\s+Show this message and exit\.', help_result.output)


PROJECT_ROOT = os.path.split(
    os.path.split(__file__)[0]
)[0]

NOW = datetime(2001, 1, 1, tzinfo=timezone.utc)
QUERY = """fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 20"""
QUERY_YAML = """fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 30
"""

CLI_ARGS = ['--group', '/aws/lambda/log_maker_a,/aws/lambda/log_maker_b', '--region', 'us-west-2',
            os.path.join(PROJECT_ROOT, 'test-assets', 'acwi.acwi'), '--start', '-30d', '--out', 'results.json', '-l',
            139]
EXPECTED_CALLS = [call(
    QUERY,
    end_time=int(NOW.timestamp()), start_time=int((NOW - timedelta(days=30)).timestamp()),
    lambda_group_names=['/aws/lambda/log_maker_a', '/aws/lambda/log_maker_b'], result_limit=139,
    out_file='results.json', region='us-west-2',
    quiet=False, jsonify=True
)]
CLI_ARGS_YAML = ['--region', 'us-east-2', os.path.join(PROJECT_ROOT, 'test-assets', 'acwi.yml'), '--out',
                 'results.json']
EXPECTED_CALLS_YAML = [call(
    QUERY_YAML,
    end_time=int(NOW.timestamp()), start_time=int(datetime(1990, 1, 1, tzinfo=timezone.utc).timestamp()),
    lambda_group_names=['/aws/lambda/a', '/aws/lambda/c'], result_limit=30, out_file=ANY, region='us-east-2',
    quiet=False, jsonify=True
)]


@pytest.mark.cli
@pytest.mark.parametrize('cli_args,expected_calls', [
    (CLI_ARGS, EXPECTED_CALLS),
    (CLI_ARGS_YAML, EXPECTED_CALLS_YAML)
])
def test_command_line_interface(monkeypatch, cli_args, expected_calls):
    mock_run_acwi = create_autospec(cli._run_acwi)
    monkeypatch.setattr(cli, '_run_acwi', mock_run_acwi)

    runner = CliRunner()
    with freeze_time(NOW):
        result = runner.invoke(cli.main, cli_args)
    assert result.exit_code == 0
    assert mock_run_acwi.call_args_list == expected_calls
