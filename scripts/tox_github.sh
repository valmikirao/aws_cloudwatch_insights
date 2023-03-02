#!/usr/bin/env bash

set -ex

PY="$1"
PY="py${PY/./}" # 3.7 -> py37
TOX_ENVS="${PY}-cli-test,${PY}-nocli-test,${PY}-cli-mpy,${PY}-nocli-mypy"
if [[ "$PY" == py311 ]]; then
    TOX_ENVS="${TOX_ENVS},lint"
fi
tox -e "$TOX_ENVS"
