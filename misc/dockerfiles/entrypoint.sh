#!/bin/sh

set -e

python setup.py install > /dev/null
"$@"
