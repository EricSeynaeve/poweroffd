# poweroffd
Daemon to automate shutdown when certain actions have finished (timeout, finished command, ...). Multiple actions can be monitored.

# Installation
- Ensure that the user running the daemon (e.g. poweroffd) can write to the logfile (default: `/var/log/poweroffd`)
- Ensure that the user running the daemon (e.g. poweroffd) can read and write in the run directory (default: `/run/poweroffd`)
- Ensure that the user running the daemon (e.g. poweroffd) can execute the poweroff command (default: `/usr/sbin/poweroff`)
- For systemd, put the services file in the normal location (e.g. `/usr/lib/systemd/system`) and enable the service (`systemctl enable poweroffd`).
- Put the files under following location (assuming the systemd configuration is used):
  - sbin/poweroffd       -> /usr/sbin/poweroffd
  - sysconfig/poweroffd  -> /usr/sysconfig/pooweroffd
  - source/poweroffd.py  -> PYTHON_SITE_PACKAGES_DIRECTORY/poweroffd.py

# Usage

Logging defaults to `/var/log/poweroffd`.

The action configuration files by default go under `/run/poweroffd`.

The configuration files are yaml files with top structure hash. These files have to end with `.conf` or they will be ignored.

Required keys are:

  - `start_time`

      seconds since the epoch when this file was created
         
  - `poweroff_on`
      
      hash to indicate when the remove this configuration
      
      Current possibilities here are:
        
      - `timeout`

          seconds to wait for the timeout
 
      - `host`

          host to follow being alive

      - `pid`

          process ID to follow till it's completed

     All these combinations are OR'ed together. So if you give a timeout and a host entry, the configuration will be removed when either the timeout is expired OR the host is not responding anymore.

     If you wish to AND configurations (e.g. only reboot when the timeout is expired AND the host is not respoding anymore), you can create multiple configuration files.
     
Example of file `my_input.conf`:

    ---
    start_time: 1435179394
    poweroff_on:
        timeout: 360
        host: somewhere

With this configuration, we indicate that the starttime is Wed Jun 24 20:56:34 2015 UCT.

This configuration will be removed when

- it is later than 21:02:34 UTC (360 seconds or 6 minutes later)
- OR the host `somewhere` is not pingable anymore.

Of course, you can also delete the configuration file to manually remove it.

Tip: use multiple configuration files to have an AND relationship:

Create a file `my_input1.conf`:

    ---
    start_time: 1435179394
    poweroff_on:
        timeout: 360

and `my_input2.conf`:

    ---
    start_time: 1435179394
    poweroff_on:
        host: somewhere

This configuration will be removed when

- it is later than 21:02:34 UTC (360 seconds or 6 minutes later)
- AND the host `somewhere` is not pingable anymore.

When all the read configurations are removed, `poweroffd` will execute the configured power-off command.

# Configuration

Poweroffd can be configured with following environment variables:

  - `POWEROFF_COMMAND`

    Indicates which command to use for powering off the system. The default is `/usr/sbin/poweroff`.

  - `LOGLEVEL`

    Defines the loglevel. Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Defaults to `INFO`.

With the provided systemd unit file, these variables can be set in `/etc/sysconfig/poweroffd`.

# Dependencies

## poweroffd

Depends on [PyYAML](https://pyyaml.org) for reading the configuration files.

Depends on [pyinotify](https://github.com/seb-m/pyinotify) to check for changes in the configuration files.

Depends on [psutil](http://pythonhosted.org/psutil/) for a more cross-platform way to work with process information.

Depends on [fping](http://fping.org/) for testing if the hosts are up in an efficient manner.

## Testing code

Uses the [pytest](http://pytest.org) library.
