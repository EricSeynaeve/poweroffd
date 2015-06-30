#! /usr/bin/env python
# vim: set ai softtabstop=2 shiftwidth=2 tabstop=80 :

import sys
import os
import os.path
import stat
import grp
import pyinotify
import time
import socket
import logging
import yaml


class Application():
  def __init__(self, logfile='/var/log/poweroffd', monitor_path='/run/poweroffd'):
    self.started_monitor = False
    # key: filename
    # value: [IP, TIMEOUT]
    self.monitor_hash = {}
    self.LOGFILE = logfile
    self.MONITOR_PATH = monitor_path
    self.LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()
    self.POWEROFF_COMMAND = os.getenv('POWEROFF_COMMAND', '/usr/sbin/poweroff')
  
  def _set_monitor_path_permissions(self):
      gid_poweroffd = grp.getgrnam('poweroffd')
      os.chown(self.MONITOR_PATH, 0, gid_poweroffd.gr_gid)
      os.chmod(self.MONITOR_PATH, 01770)

  def setup(self):
    if self.LOGLEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
      logging.basicConfig(filename=self.LOGFILE, level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S %Z', format='[%(asctime)s] %(levelname)s %(message)s')
      logging.warning("Unknown loglevel " + self.LOGLEVEL + ". Defaulting to INFO.")
    else:
      logging.basicConfig(filename=self.LOGFILE, level=eval("logging."+self.LOGLEVEL), datefmt='%Y-%m-%d %H:%M:%S %Z', format='[%(asctime)s] %(levelname)s %(message)s')

    logging.debug("Poweroff command: " + self.POWEROFF_COMMAND)
    logging.debug("Path to monitor: " + self.MONITOR_PATH)
    if not os.path.isdir(self.MONITOR_PATH):
      logging.debug("Creating monitoring dir")
      os.mkdir(self.MONITOR_PATH)
      self._set_monitor_path_permissions()

    for f in os.listdir(self.MONITOR_PATH):
      if os.path.isfile(os.path.join(self.MONITOR_PATH, f)):
        self.read_config(f)

    wm = pyinotify.WatchManager()
    self.inotify_event_handler = PoweroffdEventHandler(self)
    self.notifier = pyinotify.Notifier(wm, self.inotify_event_handler)
    wm.add_watch(self.MONITOR_PATH, pyinotify.IN_CLOSE_WRITE | pyinotify.IN_DELETE)
    
    logging.debug("Setup finished")

  def read_config(self, f):
    """
    Read the setup config file.

    The configuration file is a yaml hash consisting of the following required entries:
      - start_time: seconds since the epoch when this file was created
      - poweroff_on: hash to indicate when the remove this configuration
        Current possibilities here are:
          - timeout: seconds to wait for the timeout
          - host: host to follow being alive
        All these combinations are or'ed together. So if you give a timeout and a host
        entry, the configuration will be removed when either the timeout is expired OR
        the host is not responding anymore.
    """
    if not os.path.isabs(f):
      f = os.path.join(self.MONITOR_PATH, f)

    logging.debug("Processing " + f)
    fh = file(f)
    try:
      config_hash = yaml.safe_load(fh)

      # take the number of seconds since the epoch as an
      # integer number (precision: 1 sec)
      t = int(float(config_hash['start_time']))
      config_hash['start_time'] = t

      # convert the possible timeout value to seconds (precision: 1 sec)
      if 'timeout' in config_hash['poweroff_on']:
        s = int(float(config_hash['poweroff_on']['timeout']))
        config_hash['poweroff_on']['timeout'] = s

      # convert the possible hostname to an IP address
      if 'host' in config_hash['poweroff_on']:
        host = config_hash['poweroff_on']['host']
        ip = socket.getaddrinfo(host, None)[0][4][0]
        config_hash['poweroff_on']['host'] = ip

      self.monitor_hash[f] = config_hash
      self.started_monitor = True
    except Exception, e:
      # ignore erroneous yaml files
      logging.warning("Error was reased reading "+f+": "+str(e))
    finally:
      fh.close()

  def _process_inotify_events(self):
    if self.notifier.check_events(1000): # wait for event(s) with timeout of 1 second
      logging.debug("Processing inotify events")
      self.notifier.read_events()
      self.notifier.process_events()
    
  def _remove_entry(self, f):
    # inotify will detect the file deletion and trigger the PoweroffdEventHandler object
    # which will then delete the data structure
    os.unlink(f)

  def _check_hosts(self):
    pass

  def _check_timeouts(self):
    current_epoch = time.time()
    for f in self.monitor_hash:
      h = self.monitor_hash[f]
      po = h['poweroff_on']
      if 'timeout' in po:
        start_epoch = h['start_time']
        timeout_epoch = start_epoch + po['timeout']
        if timeout_epoch > 0 and current_epoch > timeout_epoch:
          logging.info("Removing file " + f + " due to timeout (" + str(current_epoch) + " is after " + str(timeout_epoch) + ")")
          self._remove_entry(f)

  def run(self):
    while True:
      self._process_inotify_events()
      
      self._check_hosts()
      self._check_timeouts()
      if self.started_monitor == True and len(self.monitor_hash) == 0:
        if self._poweroff():
          # executing poweroff succeeded.
          break

  def _poweroff(self):
    """
    Call the poweroff command.
    """
    # TODO: shutdown computer
    logging.info("Powering off")
    return True

class PoweroffdEventHandler(pyinotify.ProcessEvent):
  def __init__(self, app):
    pyinotify.ProcessEvent.__init__(self)
    self.app = app

  def process_IN_DELETE(self, event):
    f = event.pathname
    logging.debug("File " + f + " deleted")

    if f in self.app.monitor_hash:
      del self.app.monitor_hash[f]

  def process_IN_CLOSE_WRITE(self, event):
    f = event.pathname

    logging.debug("File " + f + " changed")
    self.app.read_config(f)

if __name__ == '__main__':
  app = Application()
  app.setup()
  try:
    app.run()
  except KeyboardInterrupt:
    sys.exit(0)
