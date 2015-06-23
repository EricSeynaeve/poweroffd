# poweroffd
Daemon to automate shutdown when certain actions have finished (timeout, finished command, ...). Multiple actions can be monitored.

# Installation
- Create a group `poweroffd`.
- Put the daemon file in `/usr/sbin`.
- For systemd, put the services file in the normal location (e.g. `/usr/lib/systemd/system`) and enable the service (`systemctl enable poweroffd`).

Logging is going to `/var/log/poweroffd`.

# Usage

The action configuration files go under `/run/poweroffd`. Only users that belong to the group `poweroffd` can write here.

# Configuration

Poweroffd can be configured with following environment variables:

  - `POWEROFF_COMMAND`

    Indicates which command to use for powering off the system. The default is `/usr/sbin/poweroff`.

  - `LOGLEVEL`

    Defines the loglevel. Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Defaults to `INFO`.

With the provided systemd unit file, these variables can be set in `/etc/sysconfig/poweroffd`.

# Dependencies

## Executing test code

Uses the [pytest](http://pytest.org) library.
