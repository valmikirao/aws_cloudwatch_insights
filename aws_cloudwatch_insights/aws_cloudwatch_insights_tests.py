from datetime import datetime
from random import random
from unittest.mock import MagicMock, call

from aws_cloudwatch_insights.aws_cloudwatch_insights import ResponseStatus, Insights


def _get_test_str() -> str:
    return f"test-{random()}"


def test_get_insights():
    mock_logs_client = MagicMock()
    fake_query_id = _get_test_str()
    mock_logs_client.start_query.return_value = {'queryId': fake_query_id}
    mock_logs_client.get_query_results.return_value = {
        'status': ResponseStatus.COMPLETE,
        'results': [
            [{'field': 'foo', 'value': '{"bar":"bing"}'}]
        ]
    }

    fake_query = _get_test_str()
    result_limit = int(random() * 1000)
    end_time = int(datetime.now().timestamp()) - int(random() * 1000)
    start_time = end_time - int(random() * 1000)

    actual_results = Insights(mock_logs_client).get_insights(
        query=fake_query,
        result_limit=result_limit,
        start_time=start_time,
        end_time=end_time,
        group_names=['/aws/lambda/log_maker']
    )

    assert actual_results == [{
        'foo': {'bar': 'bing'}
    }]
    assert mock_logs_client.start_query.call_args_list == [call(
        endTime=end_time,
        limit=result_limit,
        logGroupNames=['/aws/lambda/log_maker'],
        queryString=fake_query,
        startTime=start_time
    )]
    assert mock_logs_client.get_query_results.call_args_list == [call(queryId=fake_query_id)]


# def test_py_version():
#     # Useful for checking if one test failing will still be picked up by `make test-all`
#     import sys
#     assert sys.version.startswith('3.7.') or sys.version.startswith('3.9.')
