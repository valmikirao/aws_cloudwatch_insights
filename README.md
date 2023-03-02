# AWS Cloudwatch Insights

![version](https://img.shields.io/pypi/v/aws_cloudwatch_insights)
![python versions](https://img.shields.io/pypi/pyversions/aws_cloudwatch_insights)
![build](https://img.shields.io/github/actions/workflow/status/valmikirao/aws_cloudwatch_insights/push-workflow.yml?branch=master)

Both a command line tool and a python API to simplify interacting with AWS cloudwatch insights

## CLI

### Installation

```shell
# globally
$ pipx install 'aws_cloudwatch_insights[cli]'
# or in a particular virtual env
$ pip install 'aws_cloudwatch_insights[cli]'
```

### Usage

Run via the `acwi` command.  Results returned in json.

It takes either a file of AWS Inisghts code or a yaml file with a `query` argument and other options.

For example, if file `acwi.acwi` contained this:

```
fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 20
```

And you ran this:

```shell
$ acwi --group-names /aws/lambda/log_maker --region us-west-2 --start -30d tmp/acwi.acwi --out results.json
```

It would run the query against the stated log group in the stated region from 30 days ago.

Alternatively, if you had a file `acwi.yml` containing this:

```yaml
query: |
 fields @timestamp, @message, @logStream, @log
 | sort @timestamp desc
 | limit 20
groups:
  - /aws/lambda/log_maker
region: us-west-2
start: -30d
out_file: results.json
```

And running this:

```shell
$ acwi acwi.yml
```

You would get the same result.

If an option is on both the command line of in the .yml file, the command line overrides the value in the file.

There is some fancy partial results returned as the query runs.  You can shut these off using the `--quiet` option.

## API

If you're only using the api, you don't need to install with the `[cli]` extras.

```shell
$ pip install aws_cloudwatch_insights
```

## Usage

### Examples

```python
from aws_cloudwatch_insights import Insights
from datetime import timedelta

insights = Insights()
query = """
fields @timestamp, @message, @logStream, @log
| sort @timestamp desc
| limit 20
"""

results = insights.get_insights(
    query, group_names=["/aws/lambda/log_maker"], result_limit=20,
    start_time=-timedelta(days=1)
)

```

### Reference

From the inline documentation:

```python
class Insights:
    def __init__(self, logs_client: Optional[BaseClient] = None):
        """
        Object for querying AWS Cloudwatch.  Optionally takes a boto3 client as an argument, otherwise creates its own
        """
        ...

    def get_insights(self, query: str, result_limit: int, group_names: List[str], start_time: Union[int, datetime, timedelta],
                     end_time: Union[int, datetime, timedelta, None] = None, callback: Optional[CallbackFunction] = None,
                     error: Optional[ErrorFunction] = None, jsonify: bool = True) -> Iterable[GenericDict]:
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
        ...
```

## Development

Requires make, docker, and docker-compose:

```shell
# setting up dev environment
$ make develop

# run tests
$ make test
# ... or
$ pytest

# run tests for all environments
$ make test-all
$ make test-all-build  # checks to see if images need rebuilding
# ... you can use the underlying script to pass args to docker-compose directly:
$ ./scripts/run_tests_all.sh --build py36-no-cli py37  # runs for python 3.7 and python 3.6 with no cli

```

No CI/CD or coverage yet

## To Do
* If someone tells me they actually use this, I'll bump it to v1.0.0
* More extensive CLI unit tests
* `--csv` output option
* Integration tests

## Credits

This package was created with _cookiecutter_ and the `audreyr/cookiecutter-pypackage` project template.
