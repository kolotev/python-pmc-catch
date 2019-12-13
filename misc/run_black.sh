#!/bin/bash

source $(dirname $0)/.init.rc

ARGS=${@- --check src tests }

set -x
black -v ${ARGS[*]}

echo now you can run "$0 src tests"
