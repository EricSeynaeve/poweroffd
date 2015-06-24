#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 textwidth=180 :

import time

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
timeout_config_hash = {'start_time': int(now), 'poweroff_on': {'timeout': 30}}
host_config = """---
  start_time: """+str(now)+"""
  poweroff_on:
    host: localhost
"""
host_config_hash = {'start_time': int(now), 'poweroff_on': {'host': '127.0.0.1'}}

@pytest.fixture
def app(tmpdir):
  appl = poweroffd.Application(logfile=str(tmpdir.join('logfile')), monitor_path=str(tmpdir.join('run')))
  appl._set_monitor_path_permissions = noop
  return appl

def test_init(tmpdir, app):
  assert app.LOGLEVEL == 'INFO'
  assert app.LOGFILE == str(tmpdir.join('logfile'))
  assert app.MONITOR_PATH == str(tmpdir.join('run'))
  
def test_setup_call(tmpdir, app):
  app.setup()
  assert tmpdir.join('run').ensure(dir=True)
  assert app.monitor_hash == {}

def test_setup_call_with_file(tmpdir, app):
  tmpdir.mkdir('run')
  file1 = tmpdir.join('run','timeout_config')
  file1.write(timeout_config)
  app.setup()
  assert len(app.monitor_hash) == 1
  assert app.monitor_hash == {str(file1): timeout_config_hash}
  assert app.started_monitor == True

def test_setup_call_with_files(tmpdir, app):
  tmpdir.mkdir('run')
  file1 = tmpdir.join('run','timeout_config')
  file1.write(timeout_config)
  file2 = tmpdir.join('run','host_config')
  file2.write(host_config)
  app.setup()
  assert len(app.monitor_hash) == 2
  assert app.monitor_hash == {str(file1): timeout_config_hash, str(file2): host_config_hash}
  assert app.started_monitor == True
