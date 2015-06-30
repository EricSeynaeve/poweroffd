#! /bin/bash

SCRIPT_DIR=$(realpath "$(dirname "${BASH_SOURCE[0]}")/..")
export PYTHONPATH=$SCRIPT_DIR

py.test --cov-report term-missing --cov .. ./basic_tests.py
