#! /bin/bash

TEST_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
SCRIPT_DIR=$(realpath "$TEST_DIR/..")
export PYTHONPATH=$SCRIPT_DIR

func=''
if [[ -n ${1:-} ]]
then
	func="::$1"
fi
py.test --cov-report term-missing --cov ${SCRIPT_DIR} ${TEST_DIR}/basic_tests.py${func}
