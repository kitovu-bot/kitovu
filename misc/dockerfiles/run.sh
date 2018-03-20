#!/bin/bash

set -e

echo_green() { echo -e "\e[42m$@\e[0m"; }
echo_red()   { echo -e "\e[101m$@\e[0m"; }

echo_exec() { echo_green "$@"; "$@"; }

DIR="$(cd "$(dirname $0)"; pwd)"
ROOT_DIR="$(dirname $(dirname $DIR))"

# copy the files for the Dockerfile into the docker dir for the build
for f in Pipfile Pipfile.lock; do
  cp $ROOT_DIR/$f $DIR/$f
done

echo_exec docker build --build-arg "UID=$(id -u)" --build-arg "GID=$(id -g)" "$DIR" --tag kitovu

run_docker() {
  echo_exec docker run --rm -ti -v "$ROOT_DIR:/opt/project" kitovu "$@"
}

if [[ "$@" == "validate" ]]; then
  run_docker pylint src || echo_red "mpylint failed"
  run_docker flake8 src || echo_red "mflake8 failed"
  run_docker mypy src   || echo_red "mmypy failed"
else
  if [[ "$@" == "" ]]; then
    CMD="python"
  else
    CMD="$@"
  fi
  run_docker sh -c "python setup.py install && $CMD"
fi
