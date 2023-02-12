#!/usr/bin/env bash

set -x

PY_VERSION="$(python --version)"
PY_VERSION="${PY_VERSION/Python /}"  # just get the version number

pytest || python --version > /app/build/failed-python-"$PY_VERSION".txt
