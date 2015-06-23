#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 textwidth=180 :

import time

import pytest

from poweroffd import poweroffd

def noop():
  pass

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
