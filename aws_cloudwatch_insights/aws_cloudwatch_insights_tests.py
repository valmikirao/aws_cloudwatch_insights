import itertools
from datetime import datetime
from random import random
from secrets import token_hex
from typing import Optional, List, cast
from unittest.mock import MagicMock, call

import pytest

from aws_cloudwatch_insights.aws_cloudwatch_insights import ResponseStatus, Insights, GenericDict, ErrorFunction, \
    CallbackFunction


def test_get_insights():
    mock_logs_client = MagicMock()
    fake_query_id = f"fake-query-id-{token_hex(4)}"
    mock_logs_client.start_query.return_value = {'queryId': fake_query_id}
    mock_logs_client.get_query_results.return_value = {
        'status': ResponseStatus.COMPLETE,
        'results': [
            [{'field': 'foo', 'value': '{"bar":"bing"}'}]
        ]
    }

    fake_query = f"fake query {token_hex(4)}"
    result_limit = int(random() * 1000)
    end_time = int(datetime.now().timestamp()) - int(random() * 1000)
    start_time = end_time - int(random() * 1000)
    group_names = [
        f"/aws/lambda/test-{token_hex(4)}-1",
        f"/aws/lambda/test-{token_hex(4)}-2",
    ]

    actual_results = list(Insights(mock_logs_client).get_insights(
        query=fake_query,
        result_limit=result_limit,
        start_time=start_time,
        end_time=end_time,
        group_names=group_names
    ))

    assert actual_results == [{
        'foo': {'bar': 'bing'}
    }]
    assert mock_logs_client.start_query.call_args_list == [call(
        endTime=end_time,
        limit=result_limit,
        logGroupNames=group_names,
        queryString=fake_query,
        startTime=start_time
    )]
    assert mock_logs_client.get_query_results.call_args_list == [call(queryId=fake_query_id)]


@pytest.fixture(params=[True, False])
def with_callback(request) -> bool:
    return request.param


@pytest.fixture(params=[True, False])
def does_error_return_something(request) -> bool:
    return request.param


def test_get_insights_multi(with_callback):
    mock_logs_client = MagicMock()
    fake_query_id = f"fake-query-id-{token_hex(4)}"
    mock_logs_client.start_query.return_value = {'queryId': fake_query_id}
    final_results = [[{'field': 'foo', 'value': i}] for i in (1, 2, 3)]
    get_results_side_effects: List[GenericDict] = [{'status': ResponseStatus.SCHEDULED}]
    for i in (1, 2, 3):
        get_results_side_effects.append({
            'status': ResponseStatus.RUNNING,
            'results': final_results[:i]
        })
    get_results_side_effects[-1]['status'] = ResponseStatus.COMPLETE

    mock_logs_client.get_query_results.side_effect = get_results_side_effects

    mock_callback: Optional[MagicMock]
    if with_callback:
        mock_callback = MagicMock()
    else:
        mock_callback = None

    fake_query = f"fake query {token_hex(4)}"
    result_limit = int(random() * 1000)
    end_time = int(datetime.now().timestamp()) - int(random() * 1000)
    start_time = end_time - int(random() * 1000)
    group_names = [
        f"/aws/lambda/test-{token_hex(4)}-1",
        f"/aws/lambda/test-{token_hex(4)}-2",
    ]

    actual_results = Insights(mock_logs_client).get_insights(
        query=fake_query,
        result_limit=result_limit,
        start_time=start_time,
        end_time=end_time,
        group_names=group_names,
        callback=cast(CallbackFunction, mock_callback) if mock_callback else None
    )

    assert list(actual_results) == [{'foo': i} for i in (1, 2, 3)]
    assert mock_logs_client.start_query.call_args_list == [call(
        endTime=end_time,
        limit=result_limit,
        logGroupNames=group_names,
        queryString=fake_query,
        startTime=start_time
    )]
    assert mock_logs_client.get_query_results.call_args_list == [call(queryId=fake_query_id)] * 4

    if mock_callback is not None:
        actual_callback_calls = mock_callback.call_args_list
        expected_callback_calls = [
            [],
            [{'foo': 1}],
            [{'foo': 1}, {'foo': 2}]
        ]
        for actual, expected in itertools.zip_longest(actual_callback_calls, expected_callback_calls):
            assert actual
            actual_args, actual_kwargs = actual
            assert actual_kwargs == {}
            assert len(actual_args) == 1
            assert list(actual_args[0]) == expected


def test_get_insights_multi_error(with_callback: bool, does_error_return_something: bool):
    mock_logs_client = MagicMock()
    fake_query_id = f"fake-query-id-{token_hex(4)}"
    mock_logs_client.start_query.return_value = {'queryId': fake_query_id}
    final_results = [[{'field': 'foo', 'value': i}] for i in (1, 2)]
    get_results_side_effects = [
        {'status': ResponseStatus.SCHEDULED},
        {'status': ResponseStatus.RUNNING, 'results': final_results[:1]},
        {'status': ResponseStatus.RUNNING, 'results': final_results[:2]},
        {'status': 'Error'}
    ]

    mock_logs_client.get_query_results.side_effect = get_results_side_effects

    mock_callback: Optional[MagicMock]
    if with_callback:
        mock_callback = MagicMock()
    else:
        mock_callback = None

    mock_error_handler = MagicMock()
    fake_error_return: Optional[List[GenericDict]]
    if does_error_return_something:
        fake_error_return = [{'fake': f"return-{token_hex(4)}"}]
    else:
        fake_error_return = None
    mock_error_handler.return_value = fake_error_return

    fake_query = f"fake query {token_hex(4)}"
    result_limit = int(random() * 1000)
    end_time = int(datetime.now().timestamp()) - int(random() * 1000)
    start_time = end_time - int(random() * 1000)
    group_names = [
        f"/aws/lambda/test-{token_hex(4)}-1",
        f"/aws/lambda/test-{token_hex(4)}-2",
    ]

    actual_results = list(Insights(mock_logs_client).get_insights(
        query=fake_query,
        result_limit=result_limit,
        start_time=start_time,
        end_time=end_time,
        group_names=group_names,
        callback=cast(CallbackFunction, mock_callback) if mock_callback else None,
        error=cast(ErrorFunction, mock_error_handler)
    ))

    assert mock_logs_client.start_query.call_args_list == [call(
        endTime=end_time,
        limit=result_limit,
        logGroupNames=group_names,
        queryString=fake_query,
        startTime=start_time
    )]
    assert mock_logs_client.get_query_results.call_args_list == [call(queryId=fake_query_id)] * 4

    if mock_callback is not None:
        actual_callback_calls = mock_callback.call_args_list
        expected_callback_calls = [
            [],
            [{'foo': 1}],
            [{'foo': 1}, {'foo': 2}],
        ]
        for actual, expected in itertools.zip_longest(actual_callback_calls, expected_callback_calls):
            assert actual
            actual_args, actual_kwargs = actual
            assert actual_kwargs == {}
            assert len(actual_args) == 1
            assert list(actual_args[0]) == expected

    if does_error_return_something:
        assert actual_results == fake_error_return
    else:
        assert actual_results == []
