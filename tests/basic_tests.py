#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 textwidth=180 :

import os
import time
from threading import Timer
import logging

import pytest

from poweroffd import poweroffd

def noop():
  pass

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

@pytest.fixture
def app(tmpdir):
  os.environ['LOGLEVEL'] = 'DEBUG'
  appl = poweroffd.Application(logfile=str(tmpdir.join('logfile')), monitor_path=str(tmpdir.join('run')))
  appl._set_monitor_path_permissions = noop
  rootlogger = logging.getLogger()
  # ensure we log in the correct directory
  for h in rootlogger.handlers:
    rootlogger.removeHandler(h)
  return appl

@pytest.mark.quick
def test_init(tmpdir, app):
  assert app.LOGLEVEL == 'DEBUG'
  assert app.LOGFILE == str(tmpdir.join('logfile'))
  assert app.MONITOR_PATH == str(tmpdir.join('run'))
  
@pytest.mark.quick
def test_setup_call(tmpdir, app):
  app.setup()
  assert tmpdir.join('run').ensure(dir=True)
  assert app.monitor_hash == {}
  assert tmpdir.join('logfile').exists()

@pytest.mark.quick
def create_timeout_file(tmpdir):
  tmpdir.ensure('run', dir=True)
  f = tmpdir.join('run','timeout_config')
  f.write(timeout_config)
  return str(f)

@pytest.mark.quick
def create_host_file(tmpdir):
  tmpdir.ensure('run', dir=True)
  f = tmpdir.join('run','host_config')
  f.write(host_config)
  return str(f)

@pytest.mark.quick
def test_setup_call_with_file(tmpdir, app):
  file1 = create_timeout_file(tmpdir)
  app.setup()
  assert len(app.monitor_hash) == 1
  assert app.monitor_hash == {file1: timeout_config_hash}
  assert app.started_monitor == True

@pytest.mark.quick
def test_setup_call_with_files(tmpdir, app):
  file1 = create_timeout_file(tmpdir)
  file2 = create_host_file(tmpdir)
  app.setup()
  assert len(app.monitor_hash) == 2
  assert app.monitor_hash == {file1: timeout_config_hash, file2: host_config_hash}
  assert app.started_monitor == True

def do_timeout(tmpdir, app, timeout):
  def _emergency_break():
    app.monitor_hash = {}
    app.__EMERGENCY_APPLIED__ = True

  file1 = create_timeout_file(tmpdir)
  app.setup()
  app.monitor_hash[file1]['poweroff_on']['timeout'] = timeout
  t = Timer(2, _emergency_break, ())
  t.start()
  app.__EMERGENCY_APPLIED__ = False
  app.run()
  # application returned fine, cancel the timer now
  t.cancel()

@pytest.mark.semi_quick
def test_timeout(tmpdir, app):
  do_timeout(tmpdir, app, 1)
  assert app.__EMERGENCY_APPLIED__ == False

@pytest.mark.semi_quick
def test_timeout_expired(tmpdir, app):
  do_timeout(tmpdir, app, 5)
  assert app.__EMERGENCY_APPLIED__ == True
