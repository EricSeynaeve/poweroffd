# poweroffd
Daemon to automate shutdown when certain actions have finished (timeout, finished command, ...). Multiple actions can be monitored.

# Installation
- Create a group `poweroffd`.
- Put the daemon file in `/usr/sbin`.
- For systemd, put the services file in the normal location (e.g. `/usr/lib/systemd/system`) and enable the service (`systemctl enable poweroffd`).

Logging is going to `/var/log/poweroffd`.

# Usage

The action configuration files go under `/run/poweroffd`. Only users that belong to the group `poweroffd` can write here.
