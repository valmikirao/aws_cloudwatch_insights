"""Console script for aws_cloudwatch_insights."""
import os
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Optional

import click

from dateutil.parser import parse as parse_datetime, ParserError as DateTimeParserError

from timedeltafmt import parse_timedelta
from botocore.exceptions import ClientError
import sys
import re
import yaml
import json

import boto3

logs = boto3.client('logs')


class AsciiFlipbook:
    def __init__(self, stream=sys.stdout):
        self._last_page = ''
        self._stream = stream

    def clear(self):
        newline_count = self._last_page.count("\n")
        self._stream.write("\033[F" * newline_count)
        eraser_str = re.sub(r'\S', ' ', self._last_page)
        self._stream.write(eraser_str)
        self._stream.write("\033[F" * newline_count)
        self._stream.flush()
        self._last_page = ''

    def flip_to(self, page: str):
        self.clear()
        page_ = page + "\n" if not page.endswith("\n") else page
        self._stream.write(page_)
        self._stream.flush()
        self._last_page = page_


class Timer:
    def __init__(self):
        self.start = datetime.now()

    def elapsed(self) -> float:
        return (datetime.now() - self.start).total_seconds()


def _post_process_row(row, json_fields):
    row_ = {c["field"]: c["value"] for c in row}
    for json_field in json_fields:
        row_[json_field] = json.loads(row_[json_field])
    return row_


MAX_FLIP_WIDTH = 100


def _get_time(time_raw) -> int:
    if isinstance(time_raw, str):
        try:
            timedelta_ = parse_timedelta(time_raw)
            return int((datetime.now() + timedelta_).timestamp())
        except ValueError:
            return int(parse_datetime(time_raw).timestamp())
    elif isinstance(time_raw, dict):
        timedelta_ = timedelta(**time_raw)
        return int((datetime.now() + timedelta_).timestamp())
    else:
        time_float = float(time_raw)
        if time_float > 0:
            return int(time_float)
        else:
            return int((datetime.now() - timedelta(days=-time_float)).timestamp())


def _get_list_opt(raw_opt):
    if isinstance(raw_opt, str):
        return [raw_opt]
    else:
        return raw_opt


def yaml_loads(yaml_str):
    with StringIO(yaml_str) as fin:
        return yaml.load(fin)


class _OptionDefault:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.value)


DEFAULTS = {
    'limit': 100
}

@click.command()
@click.argument('file', required=False)
@click.option('--limit', '-l')
def main(file, **kwargs):
    """Console script for aws_cloudwatch_insights."""

    cli_opts = {k: v for k, v in kwargs.items() if v is not None}

    if file:
        fin = open(file, 'r')
    else:
        fin = sys.stdin

    try:
        input_str = fin.read()
    finally:
        if file:
            fin.close()

    try:
        file_opts = yaml_loads(input_str)
    except yaml.YAMLError:
        file_opts = {
            'query': input_str,
        }

    opts = {
        **DEFAULTS,
        **file_opts,
        **cli_opts
    }

    json.dump(opts, sys.stdout, indent=2)

    query = opts['query']
    lambda_group_names = sorted(opts['groups'])
    start_time = _get_time(opts.get('start', -1))
    end_time = _get_time(opts.get('end', 0))

    json_fields = _get_list_opt(opts.get('json_fields'))

    result_limit = int(opts.get('limit', 100))

    out_file = opts.get('out_file')

    if 'silent' in opts:
        silent = opts['silent']
    else:
        silent = not sys.stderr.isatty()

    _run_acwi(
        query,
        silent=silent,
        json_fields=json_fields,
        result_limit=result_limit,
        out_file=out_file,
        lambda_group_names=lambda_group_names,
        start_time=start_time,
        end_time=end_time
    )

    return 0


def _run_acwi(query: str, silent: bool, json_fields: List[str], result_limit: int, out_file: Optional[str],
              lambda_group_names: List[str], start_time: int, end_time: int) -> None:
    flipbook: Optional[AsciiFlipbook]
    if not silent:
        flipbook = AsciiFlipbook(stream=sys.stderr)
        flipbook.flip_to(f'Starting query with limit {result_limit}')
    else:
        flipbook = None

    response = logs.start_query(
        logGroupNames=lambda_group_names,
        startTime=start_time,
        endTime=end_time,
        queryString=query,
        limit=result_limit
    )
    query_id = response['queryId']

    def _display_progress(results_):
        assert flipbook
        page = ''
        if len(results_) > 20:
            page_results = [*results_[:10], None, *results_[-10:]]
        else:
            page_results = results_
        for row in page_results:
            if row is not None:
                row_ = _post_process_row(row, json_fields=json_fields)
                row_json = json.dumps(row_)
                terminal_size = os.get_terminal_size()
                if len(row_json) > terminal_size.columns - 2:
                    row_json = row_json[:terminal_size.columns - 5] + '...'
                page += row_json + "\n"
            else:
                page += "...\n"
        page += "\n"
        page += f"{len(results_)} / {result_limit}"
        flipbook.flip_to(page)

    results = []
    response = {}
    fout = None

    try:
        if out_file is not None:
            fout = open(out_file, 'w')
        else:
            fout = sys.stdout

        while True:
            response = logs.get_query_results(queryId=query_id)
            if response['status'] in ('Complete', 'Running'):
                results = response.get('results', [])
                if not silent:
                    _display_progress(results)
                if response['status'] == 'Complete':
                    break
            elif response['status'] != 'Scheduled':
                raise Exception(response['status'])
    finally:
        if flipbook:
            flipbook.clear()
        try:
            if len(results) > 0 and fout:
                for row in results:
                    row_ = _post_process_row(row, json_fields=json_fields)
                    print(json.dumps(row_), file=fout)
        finally:
            if fout is not sys.stdout:
                fout.close()
        if not silent and fout is not sys.stdout:
            print(f"Wrote {len(results)} rows")
        if response.get('status') != 'Complete':
            try:
                logs.stop_query(queryId=query_id)
            except ClientError:
                # probably couldn't find query to cancel
                pass


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
