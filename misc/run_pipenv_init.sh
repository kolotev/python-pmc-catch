#!/bin/bash

cd $(dirname $0)/..

pipenv --venv \
  && echo "Pipenv virtual environment already exists." \
  || { set -x; pipenv --python 3.7; }
