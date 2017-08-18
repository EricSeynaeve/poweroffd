#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 textwidth=180 :

import time
import os
import logging
import tempfile

import pytest

import poweroffd

now = time.time()
timeout_config = """---
  start_time: """+str(now)+"""
  poweroff_on:
    timeout: 30
"""
timeout_config_hash = {'start_time': int(now), 'poweroff_on': {'timeout': int(30)}}
host_config = """---
  start_time: """+str(now)+"""
  poweroff_on:
    host: localhost
"""
host_config_hash = {'start_time': int(now), 'poweroff_on': {'host': '127.0.0.1'}}
error_config = """This is a type of file"""

@pytest.fixture
def app(tmpdir):
  def noop():
    pass

  os.environ['LOGLEVEL'] = 'DEBUG'
  os.environ['POWEROFF_COMMAND'] = '/bin/true'
  appl = poweroffd.Application(logfile=str(tmpdir.join('logfile')), monitor_path=str(tmpdir.join('run')))
  appl._set_monitor_path_permissions = noop
  rootlogger = logging.getLogger()
  # ensure we log in the correct directory
  for h in rootlogger.handlers:
    rootlogger.removeHandler(h)
  return appl

@pytest.mark.quick
def test_wrong_loglevel(tmpdir, app):
  app.LOGLEVEL = 'UNEXISTING'
  app.setup()
  assert logging.getLogger().getEffectiveLevel() == logging.INFO

def create_config_file(tmpdir, basename, content):
  tmpdir.ensure('run', dir=True)
  (handle, name) = tempfile.mkstemp(dir=str(tmpdir.join('run')),prefix=basename, suffix='.conf', text=True)
  handle = os.fdopen(handle, 'w')
  handle.write(content)
  return name

def create_timeout_file(tmpdir):
  return create_config_file(tmpdir, 'timeout_config', timeout_config)

# def create_host_file(tmpdir):
#   return create_config_file(tmpdir, 'host_config', host_config)

def create_error_file(tmpdir):
  return create_config_file(tmpdir, 'error_config', error_config)

@pytest.mark.quick
def test_parse_failing_file(tmpdir, app):
  file1 = create_error_file(tmpdir)
  app.setup()
  assert len(app.monitor_hash) == 0
  assert app.monitor_hash == {}
  assert app.started_monitor == False

@pytest.mark.quick
def test_parse_ok_and_failing_file(tmpdir, app):
  file1 = create_timeout_file(tmpdir)
  file2 = create_error_file(tmpdir)
  app.setup()
  assert len(app.monitor_hash) == 1
  assert app.monitor_hash == {file1: timeout_config_hash}
  assert app.started_monitor == True
