#!/bin/bash

source $(dirname $0)/.init.rc

set -x 
mkdocs gh-deploy 
# git push github gh-pages

rsync -a --delete --stats ./site/ /pmc1/WWW/dev/ka/grlink/docs/