#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 textwidth=180 :

import os
import time
from threading import Timer
import logging
import tempfile
import subprocess
import socket
import psutil

import pytest

from poweroffd import poweroffd

# local IP address in either IPv6 or IPv4, depending on the local settings
local_ip = socket.getaddrinfo('localhost', None)[0][4][0]

timeout_config = """---
  start_time: NOW
  poweroff_on:
    timeout: 30
"""
timeout_config_hash = {'start_time': 'NOW', 'poweroff_on': {'timeout': int(30)}}
host_config = """---
  start_time: NOW
  poweroff_on:
    host: localhost
"""
host_config_hash = {'start_time': 'NOW', 'poweroff_on': {'host': local_ip}}
pid_config = """---
  start_time: NOW
  poweroff_on:
    pid: 1
"""
pid_config_hash = {'start_time': 'NOW', 'poweroff_on': {'pid': int(1)}}

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
  assert len(app.monitor_hash) == 0
  assert app.monitor_hash == {}
  assert tmpdir.join('logfile').exists()

def create_config_file(tmpdir, basename, content, now):
  tmpdir.ensure('run', dir=True)
  (handle, name) = tempfile.mkstemp(dir=str(tmpdir.join('run')),prefix=basename, suffix='.conf', text=True)
  handle = os.fdopen(handle, 'w')
  new_content = content.replace('start_time: NOW', 'start_time: '+str(int(now)))
  handle.write(new_content)
  return name

def create_timeout_file(tmpdir, now, timeout=30):
  new_timeout_config = timeout_config.replace('timeout: 30', 'timeout: '+str(timeout))
  return create_config_file(tmpdir, 'timeout_config', new_timeout_config, now)

def create_host_file(tmpdir, now):
  return create_config_file(tmpdir, 'host_config', host_config, now)

def create_pid_file(tmpdir, now, pid=1):
  new_pid_config = pid_config.replace('pid: 1', 'pid: '+str(pid))
  return create_config_file(tmpdir, 'pid_config', new_pid_config, now)

@pytest.mark.quick
def test_setup_call_with_file(tmpdir, app):
  now = int(time.time())
  file1 = create_timeout_file(tmpdir, now)
  timeout_config_hash['start_time'] = now
  app.setup()
  assert len(app.monitor_hash) == 1
  assert app.monitor_hash == {file1: timeout_config_hash}
  assert app.started_monitor == True

@pytest.mark.quick
def test_setup_call_with_file_wrong_extension(tmpdir, app):
  now = int(time.time())
  file1 = create_timeout_file(tmpdir, now)
  os.rename(file1, file1+'.bla')
  app.setup()
  assert len(app.monitor_hash) == 0
  assert app.monitor_hash == {}
  assert app.started_monitor == False

@pytest.mark.quick
def test_setup_call_with_files(tmpdir, app):
  now = int(time.time())
  file1 = create_timeout_file(tmpdir, now)
  timeout_config_hash['start_time'] = now
  file2 = create_host_file(tmpdir, now)
  host_config_hash['start_time'] = now
  file3 = create_pid_file(tmpdir, now)
  pid_config_hash['start_time'] = now
  app.setup()
  assert len(app.monitor_hash) == 3
  # first delete volatile information
  del app.monitor_hash[file3]['poweroff_on']['pid_info']
  assert app.monitor_hash == {file1: timeout_config_hash, file2: host_config_hash, \
    file3: pid_config_hash}
  assert app.started_monitor == True

def do_timeout(tmpdir, app, timeout):
  def _emergency_break():
    app.__PREV_HASH__ = app.monitor_hash
    app.monitor_hash = {}
    app.__EMERGENCY_APPLIED__ = True

  now = int(time.time())
  file1 = create_timeout_file(tmpdir, timeout, now)
  app.setup()
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

  now = int(time.time())
  file1 = create_host_file(tmpdir, now)
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

  now = int(time.time())
  file1 = create_host_file(tmpdir, now)
  file2 = create_host_file(tmpdir, now)
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

def do_pid(tmpdir, app, sub_proc):
  # ugly hack but we seem to need to poll the subprocess every time
  # otherwise python will not see it to be finished
  app.old_check_pids = app._check_pids
  def new_check_pids():
    sub_proc.poll()
    app.old_check_pids()
  app._check_pids = new_check_pids

  def _emergency_break():
    app.__PREV_HASH__ = app.monitor_hash
    app.monitor_hash = {}
    app.__EMERGENCY_APPLIED__ = True

  pid = sub_proc.pid
  now = int(time.time())
  file1 = create_pid_file(tmpdir, now, pid)
  app.setup()
  assert file1 not in app.erroneous_files
  t = Timer(2, _emergency_break, ())
  t.start()
  app.__EMERGENCY_APPLIED__ = False
  app.run()
  # application returned fine, cancel the timer now
  t.cancel()

@pytest.mark.semi_quick
def test_read_new_file(tmpdir, app):
  def _emergency_break():
    app.__PREV_HASH__ = app.monitor_hash
    app.monitor_hash = {}
    app.__EMERGENCY_APPLIED__ = True

  now = int(time.time())
  t = Timer(2, _emergency_break, ())
  t.start()
  app.setup()
  assert len(app.monitor_hash) == 0
  assert app.started_monitor == False
  file1 = create_host_file(tmpdir, now)
  host_config_hash['start_time'] = now
  # If there is a failure reading the above file, we won't
  # be able to interrupt the app because it thinks nothing
  # is still monitored
  app.started_monitor = True
  app.__EMERGENCY_APPLIED__ = False
  app.run()
  # application returned fine, cancel the timer now
  t.cancel()
  assert len(app.__PREV_HASH__) == 1
  assert app.__PREV_HASH__ == {file1: host_config_hash}
  assert app.started_monitor == True
  assert app.__EMERGENCY_APPLIED__ == True

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
  do_host(tmpdir, app, local_ip)
  assert app.__EMERGENCY_APPLIED__ == True
  assert len(app.__PREV_HASH__) == 1

@pytest.mark.semi_quick
def test_host_down(tmpdir, app):
  do_host(tmpdir, app, '0.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == False

@pytest.mark.semi_quick
def test_host_up_host_down(tmpdir, app):
  do_hosts(tmpdir, app, local_ip, '0.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == True
  assert len(app.__PREV_HASH__) == 1

@pytest.mark.semi_quick
def test_same_host_twice_up(tmpdir, app):
  do_hosts(tmpdir, app, local_ip, local_ip)
  assert app.__EMERGENCY_APPLIED__ == True
  assert len(app.__PREV_HASH__) == 2

@pytest.mark.semi_quick
def test_same_host_twice_down(tmpdir, app):
  do_hosts(tmpdir, app, '0.0.0.1', '0.0.0.1')
  assert app.__EMERGENCY_APPLIED__ == False

@pytest.mark.semi_quick
def test_pid_done(tmpdir, app):
  sub_proc = subprocess.Popen(['/usr/bin/sleep', '1'])

  do_pid(tmpdir, app, sub_proc)
  assert app.__EMERGENCY_APPLIED__ == False

@pytest.mark.semi_quick
def test_pid_not_done(tmpdir, app):
  sub_proc = subprocess.Popen(['/usr/bin/sleep', '3'])
  do_pid(tmpdir, app, sub_proc)
  assert app.__EMERGENCY_APPLIED__ == True

def test_pid_not_there_anymore_during_setup(tmpdir, app):
  def raise_failure(pid):
    raise psutil.NoSuchProcess(pid, 'mocked')
  app._get_process_dict = raise_failure

  sub_proc = subprocess.Popen(['/usr/bin/sleep', '1'])
  pid = sub_proc.pid
  now = int(time.time())
  file1 = create_pid_file(tmpdir, now, pid)
  app.setup()
  assert len(app.monitor_hash) == 0
  assert file1 not in app.erroneous_files

@pytest.mark.semi_quick
def test_pid_not_there_anymore_during_run(tmpdir, app):
  old_get_process_dict = app._get_process_dict
  def raise_failure(pid):
    if raise_failure.call_count == 0:
      raise_failure.call_count += 1
      return old_get_process_dict(pid)
    else:
      raise psutil.NoSuchProcess(pid, 'mocked')
  raise_failure.call_count = 0
  app._get_process_dict = raise_failure

  sub_proc = subprocess.Popen(['/usr/bin/sleep', '3'])
  do_pid(tmpdir, app, sub_proc)
  assert app.__EMERGENCY_APPLIED__ == False

@pytest.mark.semi_quick
def test_pid_different_process(tmpdir, app):
  old_get_process_dict = app._get_process_dict
  def raise_failure(pid):
    if raise_failure.call_count == 0:
      raise_failure.call_count += 1
      return old_get_process_dict(pid)
    else:
      d = old_get_process_dict(pid)
      d['create_time'] += 600
      return d

  raise_failure.call_count = 0
  app._get_process_dict = raise_failure

  sub_proc = subprocess.Popen(['/usr/bin/sleep', '3'])
  do_pid(tmpdir, app, sub_proc)
  assert app.__EMERGENCY_APPLIED__ == False
