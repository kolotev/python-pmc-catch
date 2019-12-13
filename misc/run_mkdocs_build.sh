#!/bin/bash

source $(dirname $0)/.init.rc

mkdocs build "$@"
