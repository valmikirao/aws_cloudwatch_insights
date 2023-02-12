"""Console script for aws_cloudwatch_insights."""
import os
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Optional, Dict, Any, Iterable

import boto3
import click

from dateutil.parser import parse as parse_datetime

from timedeltafmt import parse_timedelta
import sys
import re
import yaml
import json

from .aws_cloudwatch_insights import GenericDict, CallbackFunction, Insights

STDOUT_FD = 1
STDERR_FD = 2


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


def _get_list_opt(raw_opt, split_with=None):
    if isinstance(raw_opt, str) and split_with is None:
        return [raw_opt]
    elif isinstance(raw_opt, str):
        return raw_opt.split(split_with)
    else:
        return raw_opt


def _yaml_loads(yaml_str):
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
    'limit': 100,
    'start': '-1d',
    'end': 0,
    'jsonify': True,
    'out_file': None,
    'region': None
}


def _consolidate_opts(file, kwargs):
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

    file_opts: Dict[str, Any]
    try:
        file_opts = _yaml_loads(input_str)
        if not isinstance(file_opts, dict):
            file_opts = {'query': input_str}
    except yaml.YAMLError:
        file_opts = {'query': input_str}

    opts = {
        **DEFAULTS,
        **file_opts,
        **cli_opts
    }
    return opts


def _run_acwi(query: str, silent: bool, result_limit: int, out_file: Optional[str], lambda_group_names: List[str],
              start_time: int, end_time: int, jsonify: bool, region: Optional[str]) -> None:
    logs_client = boto3.client('logs', region_name=region)

    flipbook: Optional[AsciiFlipbook]
    if not silent:
        flipbook = AsciiFlipbook(stream=sys.stderr)
        flipbook.flip_to(f'Starting query with limit {result_limit}')
    else:
        flipbook = None

    def _display_progress(results_: Iterable[GenericDict]) -> None:
        assert flipbook
        page = ''
        results_ = list(results_)
        if len(results_) > 20:
            page_results = [*results_[:10], None, *results_[-10:]]
        else:
            page_results = results_
        for row in page_results:
            if row is not None:
                row_json = json.dumps(row)
                terminal_size = os.get_terminal_size(STDERR_FD)
                if len(row_json) > terminal_size.columns - 2:
                    row_json = row_json[:terminal_size.columns - 5] + '...'
                page += row_json + "\n"
            else:
                page += "...\n"
        page += "\n"
        page += f"{len(results_)} / {result_limit}"
        flipbook.flip_to(page)

    callback: Optional[CallbackFunction]
    if not silent and os.isatty(STDERR_FD):
        callback = _display_progress
    else:
        callback = None

    if out_file is not None:
        fout = open(out_file, 'w')
    else:
        fout = sys.stdout

    results: Iterable[GenericDict] = []

    def _handle_error(error: BaseException, results_so_far: Iterable[GenericDict]) -> None:
        nonlocal results
        results = results_so_far
        raise error

    try:
        results = Insights(logs_client).get_insights(
            query=query,
            result_limit=result_limit,
            group_names=lambda_group_names,
            start_time=start_time,
            end_time=end_time,
            jsonify=jsonify,
            callback=callback,
            error=_handle_error
        )
    finally:
        if flipbook:
            flipbook.clear()
        rows_written = 0
        try:
            if fout:
                for row in results:
                    print(json.dumps(row), file=fout)
                    rows_written += 1
        finally:
            if fout is not sys.stdout:
                fout.close()
        if not silent and (
            fout is not sys.stdout
            # if stdout is being piped somewhere but stderr is still a tty
            or (os.isatty(STDERR_FD) and not os.isatty(STDOUT_FD))
        ):
            print(f"Wrote {rows_written} rows")


@click.command()
@click.argument('file', required=False)
@click.option('--limit', '-l')
@click.option('--start', '-s')
@click.option('--end', '-e')
@click.option('--jsonify/--no-jsonify', '-j/-J', default=True)
@click.option('--groups', '--group', '-g')
@click.option('--out-file', '--out', '-o')
@click.option('--region', '-r')
def main(file, **kwargs):
    """Console script for aws_cloudwatch_insights."""
    opts = _consolidate_opts(file, kwargs)

    query = opts['query']
    jsonify = opts['jsonify']
    lambda_group_names = sorted(_get_list_opt(opts['groups'], split_with=','))
    start_time = _get_time(opts['start'])
    end_time = _get_time(opts['end'])

    result_limit = int(opts['limit'])

    out_file = opts['out_file']

    if 'silent' in opts:
        silent = opts['silent']
    else:
        silent = not sys.stderr.isatty()

    region = opts['region']

    _run_acwi(
        query,
        silent=silent,
        result_limit=result_limit,
        out_file=out_file,
        lambda_group_names=lambda_group_names,
        start_time=start_time,
        end_time=end_time,
        jsonify=jsonify,
        region=region
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
