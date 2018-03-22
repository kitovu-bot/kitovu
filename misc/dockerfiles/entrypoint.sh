#!/bin/sh

set -e

pipenv run python setup.py install

pipenv run "$@"
