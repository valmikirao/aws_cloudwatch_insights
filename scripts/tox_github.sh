#!/usr/bin/env bash

set -ex

PY="$1"
PY="py${PY/./}" # 3.7 -> py37
TOX_ENVS="${PY}-cli,${PY}-nocli"
if [[ "$PY" == py37 ]]; then
    TOX_ENVS="${TOX_ENVS},lint"
fi
tox -e "$TOX_ENVS"
