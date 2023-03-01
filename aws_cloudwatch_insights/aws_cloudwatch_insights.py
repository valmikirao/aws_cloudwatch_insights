"""Main module."""
import json
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import List, Optional, Dict, Any, Callable, Iterable, Union

import boto3
from botocore.exceptions import ClientError

try:
    from mypy_boto3_logs import CloudWatchLogsClient
    from mypy_boto3_logs.type_defs import GetQueryResultsResponseTypeDef, ResultFieldTypeDef
except ModuleNotFoundError:
    # don't want to make stubs required
    CloudWatchLogsClient = Any  # type: ignore
    GetQueryResultsResponseTypeDef = Any  # type: ignore
    ResultFieldTypeDef = Any  # type: ignore


GenericDict = Dict[str, Any]
CallbackFunction = Callable[[Iterable[GenericDict]], Any]
ErrorFunction = Callable[[BaseException, Iterable[GenericDict]], Optional[Iterable[GenericDict]]]


class ResponseStatus:
    COMPLETE = 'Complete'
    RUNNING = 'Running'
    SCHEDULED = 'Scheduled'


"""
import time
from botocore.client import BaseClient
from dataclasses import dataclass

@dataclass
class TestingClient:
    logs: BaseClient
    calls_to_make: int
    items_per_call: int = 2
    _call_count: int = 0
    _cached_response: Optional[GenericDict] = None

    def start_query(self, *args, **kwargs) -> GenericDict:
        return self.logs.start_query(*args, **kwargs)

    def get_query_results(self, *args, **kwargs) -> GenericDict:
        time.sleep(1.5)
        self._call_count += 1
        if self._cached_response is None:
            response = self.logs.get_query_results(*args, **kwargs)
            if response['status'] == ResponseStatus.COMPLETE:
                self._cached_response = deepcopy(response)
        else:
            response = deepcopy(self._cached_response)
        if self._call_count >= self.calls_to_make:
            assert response['status'] == ResponseStatus.COMPLETE
            # do nothing
        else:
            response['status'] = ResponseStatus.RUNNING
            results_len = self.items_per_call * self._call_count
            results = response.get('results', [])
            response['results'] = results[:results_len]

        return response

    def stop_query(self, *args, **kwargs):
        self.logs.stop_query(*args, **kwargs)
"""


class InsightsRemoteException(Exception):
    def __init__(self, status):
        super(f"AWS Returned Invalid Status: {status!r}")
        self.status = status


def jsonify_insights_results(results: Iterable[GenericDict]) -> Iterable[GenericDict]:
    for row in results:
        returned_row = {}
        for key, value in row.items():
            if isinstance(value, str) and value.startswith('{'):
                try:
                    parsed_value = json.loads(value)
                    returned_row[key] = parsed_value
                except JSONDecodeError:
                    returned_row[key] = value
            else:
                returned_row[key] = value

            yield returned_row


def dictify_results(results: Iterable[Iterable[ResultFieldTypeDef]]) -> Iterable[GenericDict]:
    for row in results:
        returned_row = {i['field']: i['value'] for i in row}
        yield returned_row


class Insights:
    def __init__(self, logs_client: Optional[CloudWatchLogsClient] = None):
        """
        Object for querying AWS Cloudwatch.  Optionally takes a boto3 client as an argument, otherwise creates its own
        """
        if logs_client:
            self.logs_client = logs_client
        else:
            self.logs_client = boto3.client('logs')

    def get_insights(self, query: str, result_limit: int, group_names: List[str],
                     start_time: Union[int, datetime, timedelta],
                     end_time: Union[int, datetime, timedelta, None] = None,
                     callback: Optional[CallbackFunction] = None, error: Optional[ErrorFunction] = None,
                     jsonify: bool = True) -> Iterable[GenericDict]:
        """
        Gets elements from AWS Cloudwatch Logs using an Insights query:

        Returns an iterable of dicts

        query: The Insights query
        result_limit: Limit of the number of results returned
        group_names: The log groups searched through
        start_time: The time of the earliest record the query looks for.  Can be an int timestamp, a datetime, or a
         timedelta.  If it's a timedelta, the start time is now offset by the delta
        end_time: The time of the latest record the query looks for.  Accepts same values as `start_time`
        callback: A function witch is called when partial results are returned, before the function returns the final
            results.  Takes the partial results as an argument.
        error: If included, this function is called when an exception is encountered (instead of not catching the
          exception).  The arguments passed to the function are the Exception instance and the partial results.  If
          this function doesn't through an exception, get_insights() returns the returned value of this function, empty
          list if that value is None
        jsonify: If set to True, attempts to parse suspected json objects.  If parsing fails, just returns the string.
          Default: True
        """
        if end_time is None:
            end_time = datetime.now()

        def _normalize_time(time: Union[int, datetime, timedelta]) -> int:
            if isinstance(time, int):
                return time
            elif isinstance(time, datetime):
                return int(time.timestamp())
            elif isinstance(time, timedelta):
                return int((datetime.now() + time).timestamp())
            else:
                raise NotImplementedError()
        start_time = _normalize_time(start_time)
        end_time = _normalize_time(end_time)

        start_query_response = self.logs_client.start_query(
            logGroupNames=group_names,
            startTime=start_time,
            endTime=end_time,
            queryString=query,
            limit=result_limit
        )
        query_id = start_query_response['queryId']
        results: Iterable[GenericDict] = []
        response: Union[GenericDict, GetQueryResultsResponseTypeDef] = {}

        def _post_process_results(results_raw_: List[List[ResultFieldTypeDef]]) -> Iterable[GenericDict]:
            results_ = dictify_results(results_raw_)
            if jsonify:
                results_ = jsonify_insights_results(results_)
            return results_

        try:
            while True:
                response = self.logs_client.get_query_results(queryId=query_id)
                results_raw = response.get('results', [])
                response_status = response['status']
                if response_status in {ResponseStatus.RUNNING, ResponseStatus.SCHEDULED} and callback is not None:
                    results = _post_process_results(results_raw)
                    callback(results)
                elif response_status == ResponseStatus.COMPLETE:
                    results = _post_process_results(results_raw)
                    break
                elif response_status not in {ResponseStatus.RUNNING, ResponseStatus.SCHEDULED, ResponseStatus.COMPLETE}:
                    raise InsightsRemoteException(response_status)
        except BaseException as e:
            if error:
                error_results = error(e, results)
                if error_results is not None:
                    results = error_results
                else:
                    results = []
            else:
                raise
        finally:
            if response.get('status') != ResponseStatus.COMPLETE:
                try:
                    self.logs_client.stop_query(queryId=query_id)
                except ClientError:
                    # probably couldn't find query to cancel
                    pass

        return results
