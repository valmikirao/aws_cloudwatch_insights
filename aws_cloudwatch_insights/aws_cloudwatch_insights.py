"""Main module."""
import json
from json import JSONDecodeError
from typing import List, Optional, Dict, Any, Callable, Iterable

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError


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


def dictify_results(results: Iterable[Iterable[GenericDict]]) -> Iterable[GenericDict]:
    for row in results:
        returned_row = {i['field']: i['value'] for i in row}
        yield returned_row


class Insights:
    def __init__(self, logs_client: Optional[BaseClient] = None):
        if logs_client:
            self.logs_client = logs_client
        else:
            self.logs_client = boto3.client('logs')

    def get_insights(self, query: str, result_limit: int, lambda_group_names: List[str], start_time: int,
                     end_time: int, callback: Optional[CallbackFunction] = None, error: Optional[ErrorFunction] = None,
                     jsonify: bool = True) -> Iterable[GenericDict]:
        response = self.logs_client.start_query(
            logGroupNames=lambda_group_names,
            startTime=start_time,
            endTime=end_time,
            queryString=query,
            limit=result_limit
        )
        query_id = response['queryId']
        results: Iterable[GenericDict] = []
        response: GenericDict = {}
        try:
            while True:
                response = self.logs_client.get_query_results(queryId=query_id)
                if response['status'] in (ResponseStatus.COMPLETE, ResponseStatus.RUNNING):
                    results_: List[List[GenericDict]] = response.get('results', [])
                    results = dictify_results(results_)
                    if jsonify:
                        results = list(jsonify_insights_results(results))
                    if callback:
                        callback(results)
                    if response['status'] == ResponseStatus.COMPLETE:
                        break
                elif response['status'] != ResponseStatus.SCHEDULED:
                    raise InsightsRemoteException(response['status'])
        except BaseException as e:
            if error:
                return list(error(e, results))
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
