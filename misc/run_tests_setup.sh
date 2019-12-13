#!/bin/bash
# export DJANGO_SETTINGS_MODULE=project.settings_test
source $(dirname $0)/.init.rc

set -x
python setup.py test "$@"
