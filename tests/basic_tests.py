#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 textwidth=180 :

import os
import time
from threading import Timer
import logging
import tempfile

import pytest

from poweroffd import poweroffd

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
def test_init(tmpdir, app):
  assert app.LOGLEVEL == 'DEBUG'
  assert app.POWEROFF_COMMAND == '/bin/true'
  assert app.LOGFILE == str(tmpdir.join('logfile'))
  assert app.MONITOR_PATH == str(tmpdir.join('run'))
  
@pytest.mark.quick
def test_setup_call(tmpdir, app):
  app.setup()
  assert tmpdir.join('run').ensure(dir=True)
  assert app.monitor_hash == {}
  assert tmpdir.join('logfile').exists()

def create_config_file(tmpdir, basename, content):
  tmpdir.ensure('run', dir=True)
  (handle, name) = tempfile.mkstemp(dir=str(tmpdir.join('run')),prefix=basename, text=True)
  handle = os.fdopen(handle, 'w')
  handle.write(content)
  return name

def create_timeout_file(tmpdir):
  return create_config_file(tmpdir, 'timeout_config', timeout_config)

def create_host_file(tmpdir):
  return create_config_file(tmpdir, 'host_config', host_config)

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
    app.__PREV_HASH__ = app.monitor_hash
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

def do_host(tmpdir, app, ip):
  def _emergency_break():
    app.__PREV_HASH__ = app.monitor_hash
    app.monitor_hash = {}
    app.__EMERGENCY_APPLIED__ = True

  file1 = create_host_file(tmpdir)
  app.setup()
  app.monitor_hash[file1]['poweroff_on']['host'] = ip
  t = Timer(2, _emergency_break, ())
  t.start()
  app.__EMERGENCY_APPLIED__ = False
  app.run()
  # application returned fine, cancel the timer now
  t.cancel()

def do_hosts(tmpdir, app, ip1, ip2):
  def _emergency_break():
    app.__PREV_HASH__ = app.monitor_hash
    app.monitor_hash = {}
    app.__EMERGENCY_APPLIED__ = True

  file1 = create_host_file(tmpdir)
  file2 = create_host_file(tmpdir)
  app.setup()
  assert len(app.monitor_hash) == 2
  app.monitor_hash[file1]['poweroff_on']['host'] = ip1
  app.monitor_hash[file2]['poweroff_on']['host'] = ip2
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
  assert len(app.__PREV_HASH__) == 1

@pytest.mark.semi_quick
def test_host_up(tmpdir, app):
  do_host(tmpdir, app, '127.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == True
  assert len(app.__PREV_HASH__) == 1

@pytest.mark.semi_quick
def test_host_down(tmpdir, app):
  do_host(tmpdir, app, '0.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == False

@pytest.mark.semi_quick
def test_host_up_host_down(tmpdir, app):
  do_hosts(tmpdir, app, '127.0.0.1', '0.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == True
  assert len(app.__PREV_HASH__) == 1

@pytest.mark.semi_quick
def test_same_host_twice_up(tmpdir, app):
  do_hosts(tmpdir, app, '127.0.0.1', '127.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == True
  assert len(app.__PREV_HASH__) == 2

@pytest.mark.semi_quick
def test_same_host_twice_down(tmpdir, app):
  do_hosts(tmpdir, app, '0.0.0.1', '0.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == False
