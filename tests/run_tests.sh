#! /bin/bash

TEST_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
SCRIPT_DIR=$(realpath "$TEST_DIR/../source")
export PYTHONPATH=$SCRIPT_DIR

func=''
files="${TEST_DIR}/basic_tests.py${func} ${TEST_DIR}/invalid_input.py${func}"
if (( $# > 0 ))
then
	if [[ -n ${1:-} ]]
	then
		test_file=$(grep -l "^def $1[^a-zA-Z0-9_]" ${TEST_DIR}/*.py)
		files="$test_file::$1"
	fi
	shift
fi
py.test --cov-report term-missing --cov ${SCRIPT_DIR} "$@" $files
