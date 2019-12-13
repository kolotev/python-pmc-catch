#!/bin/bash

source $(dirname $0)/.init.rc

ARGS=${@- src tests }

set -x
flake8 ${ARGS[*]}
