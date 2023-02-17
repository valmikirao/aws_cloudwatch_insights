#!/usr/bin/env bash

set -ex

PY_VERSION="$(python --version)"
PY_VERSION="${PY_VERSION/Python /}"  # just get the version number
ARG_HASH="$(printf '%q ' "$@" | sha1sum)"
ARG_HASH="${ARG_HASH::8}"
pytest "$@" || echo "$(python --version)" "$(printf '%q ' "$@")" > /app/build/failed-python-"$PY_VERSION"-"$ARG_HASH".txt
