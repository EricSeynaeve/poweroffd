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
    if not os.path.isabs(f):
      f = os.path.join(self.MONITOR_PATH, f)

    logging.debug("Processing " + f)
    for line in file(f):
      try:
        (host, epoch, timeout) = line.split()
        ip = socket.getaddrinfo(host, None)[0][4][0]
        timeout_epoch = int(epoch) + int(timeout)
        logging.info(f + " ==> " + str( (ip, timeout_epoch) ) )
        self.monitor_hash[f] = (ip, timeout_epoch)
        self.started_monitor = True
      except:
        # ignore any malprocessed lines
        pass

  def _process_inotify_events(self):
    if self.notifier.check_events(1000): # wait for event(s) with timeout of 1 second
      logging.debug("Processing inotify events")
      self.notifier.read_events()
      self.notifier.process_events()
    
  def run(self):
    while True:
      self._process_inotify_events()
      
      current_epoch = time.time()
      for f in self.monitor_hash:
        (ip, timeout_epoch) = self.monitor_hash[f]
        if timeout_epoch > 0 and current_epoch > timeout_epoch:
          logging.info("Removing file " + f + " due to timeout (" + str(current_epoch) + " after " + str(timeout_epoch) + ")")
          os.unlink(f)

  def _shutdown(self):
    # TODO: shutdown computer
    logging.info("Shutting down")

class PoweroffdEventHandler(pyinotify.ProcessEvent):
  def __init__(self, app):
    pyinotify.ProcessEvent.__init__(self)
    self.app = app

  def process_IN_DELETE(self, event):
    f = event.pathname
    logging.debug("File " + f + " deleted")

    if f in self.app.monitor_hash:
      del self.app.monitor_hash[f]

    if self.app.started_monitor == True and len(self.app.monitor_hash) == 0:
      self.app._shutdown()

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
