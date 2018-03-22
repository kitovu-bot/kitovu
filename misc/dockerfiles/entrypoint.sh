#!/bin/sh

set -e

pipenv run python setup.py install > /dev/null

pipenv run "$@"
