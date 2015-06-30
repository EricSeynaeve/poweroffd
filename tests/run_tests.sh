#! /bin/bash

SCRIPT_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")/..")
export PYTHONPATH=$SCRIPT_DIR

func=''
if [[ -n ${1:-} ]]
then
	func="::$1"
fi
py.test --cov-report term-missing --cov .. ./basic_tests.py${func}
