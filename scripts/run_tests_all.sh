#!/usr/bin/env bash

set -ex

PROJECT_DIR="$(dirname "$(dirname $0)")"
FAILED_PYTHON_VERSIONS_FILES=($PROJECT_DIR/build/failed-python-*.txt)

if [[ -e "${FAILED_PYTHON_VERSIONS_FILES[0]}" ]]; then
    rm "${FAILED_PYTHON_VERSIONS_FILES[@]}"
fi

docker-compose -f docker-compose.test.yml up "$@"

FAILED_PYTHON_VERSIONS_FILES=($PROJECT_DIR/build/failed-python-*.txt)

if [[ -e "${FAILED_PYTHON_VERSIONS_FILES[0]}" ]]; then
    set +x # less confusing output, please
    echo >&2
    echo -------------------------------------------------------------------------------------------- >&2
    echo Tests Failed for These Versions of Python: >&2
    cat "${FAILED_PYTHON_VERSIONS_FILES[@]}" >&2
    echo -------------------------------------------------------------------------------------------- >&2
    echo >&2
    exit 1
else
    set +x
    echo
    echo --------------------------------------------------------------------------------------------
    echo 'Success!!!'
    echo --------------------------------------------------------------------------------------------
    echo
fi
