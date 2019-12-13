#!/bin/bash

source $(dirname $0)/.init.rc

set -x
pip install "$@"