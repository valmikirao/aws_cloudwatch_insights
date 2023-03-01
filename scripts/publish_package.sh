#!/usr/bin/env bash

set -e  # would also like to set -x, but some variable values are secrets

function assert_env() {
    local ENV_NAME="$1"
    local ENV_VALUE="$(eval 'echo $'$ENV_NAME)"
    if [[ ! "$ENV_VALUE" ]]; then
        echo "Env Variable \$$ENV_NAME is required for deployment" >&2
        exit 1
    fi
}

assert_env PYPI_PASSWORD
assert_env GITHUB_RELEASE_VERSION
assert_env BRANCH

SCRIPTS_DIR="$(dirname "$0")"
VERSION="$(python "${SCRIPTS_DIR}/print_version.py")"

if [[ "$GITHUB_RELEASE_VERSION" !=  "$VERSION" ]]; then
    echo "\$GITHUB_RELEASE version ($GITHUB_RELEASE_VERSION) is not the same as the version referenced" >&2
    echo "in the code ($VERSION).  Exiting" >&2
    exit 2
fi

if [[ "$BRANCH" != master ]] && ! grep -q a <<< "$VERSION"; then
    echo "Version $VERSION invalid for branch $BRANCH: only alpha release can be done on non-master branches" >&2
    exit 3
fi

pip install -r requirements_publish.txt
make publish
