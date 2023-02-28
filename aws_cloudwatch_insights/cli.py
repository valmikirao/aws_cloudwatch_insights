"""Console script for aws_cloudwatch_insights."""
import os
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Optional, Dict, Any, Iterable, TextIO, cast

import boto3
from yaml import Loader

try:
    import click
    from timedeltafmt import parse_timedelta
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(f"{e.msg}, you may need to install the cli: `pip install aws_cloudwatch_insights[cli]`")

from dateutil.parser import parse as parse_datetime


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
        return yaml.load(fin, Loader)


class _OptionDefault:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.value)


class Fields:
    query = 'query'
    limit = 'limit'
    start = 'start'
    end = 'end'
    jsonify = 'jsonify'
    out_file = 'out_file'
    region = 'region'
    quiet = 'quiet'
    groups = 'groups'


DEFAULTS = {
    Fields.limit: 100,
    Fields.start: '-1d',
    Fields.end: '-0s',
    Fields.jsonify: True,
    Fields.out_file: None,
    Fields.region: None,
    Fields.quiet: False,
}


def _consolidate_opts(file, kwargs):
    cli_opts = {k: v for k, v in kwargs.items() if v is not None}
    if file and file != '-':
        fin = open(file, 'r')
    else:
        fin = sys.stdin
    try:
        input_str = fin.read()
    finally:
        if fin is not sys.stdin:
            fin.close()

    file_opts: Dict[str, Any]
    try:
        file_opts = _yaml_loads(input_str)
        if not isinstance(file_opts, dict) or 'query' not in file_opts:
            file_opts = {'query': input_str}
    except yaml.YAMLError:
        file_opts = {'query': input_str}

    opts = {
        **DEFAULTS,
        **file_opts,
        **cli_opts
    }
    return opts


def _run_acwi(query: str, quiet: bool, result_limit: int, out_file: Optional[str], lambda_group_names: List[str],
              start_time: int, end_time: int, jsonify: bool, region: Optional[str]) -> None:
    logs_client = boto3.client('logs', region_name=region)

    flipbook: Optional[AsciiFlipbook]
    if not quiet:
        flipbook = AsciiFlipbook(stream=sys.stderr)
        flipbook.flip_to(f'Starting query with limit {result_limit}')
    else:
        flipbook = None

    def _display_progress(results: Iterable[GenericDict]) -> None:
        assert flipbook
        page = ''
        results_ = list(results)
        page_results: List[Optional[GenericDict]]
        if len(results_) > 20:
            page_results = [*results_[:10], None, *results_[-10:]]
        else:
            page_results = cast(List[Optional[GenericDict]], results_)
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
    if not quiet and os.isatty(STDERR_FD):
        callback = _display_progress
    else:
        callback = None

    fout: TextIO
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
        if not quiet and (
            fout is not sys.stdout
            # if stdout is being piped somewhere but stderr is still a tty
            or (os.isatty(STDERR_FD) and not os.isatty(STDOUT_FD))
        ):
            print(f"Wrote {rows_written} rows")


@click.command()
@click.argument('file')
@click.option('--limit', '-l', help=f"The maximum number or items returned. Default {DEFAULTS[Fields.limit]!r}."
                                    f" Yaml file field: {Fields.limit!r}")
@click.option('--start', '-s', help=f"Earliest record the query will search for.  Can be an integer timestamp, an iso"
                                    f" date, or a relative indicator with dhms: 1000, '2023-02-20T14:56:40-05:00', or"
                                    f" '-3d'.  Default: {DEFAULTS[Fields.start]!r}.  Yaml file field: {Fields.start!r}")
@click.option('--end', '-e', help=f"Latest record the query will search for.  Can be an integer timestamp, an iso date,"
                                  f" or a relative indicator with dhms. Default: {DEFAULTS[Fields.end]!r} (now).  Yaml"
                                  f" file field: {Fields.end!r}")
@click.option('--jsonify/--no-jsonify', '-j/-J', default=True,
              help=f"When true, attempts to parse fields that look like they might be json object into a json"
                   f" structure. If it can't parse the fields, leaves them as string.  Default:"
                   f" {DEFAULTS[Fields.jsonify]!r}.  Yaml file field: {Fields.jsonify!r}")
@click.option('--groups', '--group', '-g', help=f"A comma delimited list of the log groups to search through.  No"
                                                f" Default.  Yaml file field: {Fields.groups!r}")
@click.option('--out-file', '--out', '-o', help=f"If included, outputs results to stated file.  Default is standard"
                                                f" out.  Yaml file field: {Fields.out_file!r}")
@click.option('--region', '-r', help=f"AWS Region.  If excluded, uses system default.  Yaml file field:"
                                     f" {Fields.region!r}")
@click.option('--quiet/--not-quiet', '-q/-Q', help=f"If true, will not give status outputs to standard error.  Default"
                                                   f" is {DEFAULTS[Fields.quiet]}.  Yaml file field: {Fields.quiet!r}")
def main(file, **kwargs):
    """
    Console script for aws_cloudwatch_insights. FILE is a file either containing just the AWS Insights query or a
     yaml file with a `query` field and other options.

    Returns items in a .jsonl format
    """
    opts = _consolidate_opts(file, kwargs)

    query = opts[Fields.query]
    jsonify = opts[Fields.jsonify]
    lambda_group_names = sorted(_get_list_opt(opts[Fields.groups], split_with=','))
    start_time = _get_time(opts[Fields.start])
    end_time = _get_time(opts[Fields.end])

    result_limit = int(opts[Fields.limit])

    out_file = opts[Fields.out_file]

    if Fields.quiet in opts:
        quiet = opts[Fields.quiet]
    else:
        quiet = not sys.stderr.isatty()

    region = opts[Fields.region]

    _run_acwi(
        query,
        quiet=quiet,
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
