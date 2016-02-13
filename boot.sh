#!/bin/bash
### BEGIN INIT INFO
# Provides:          scriptname
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start daemon at boot time
# Description:       Enable service provided by daemon.
### END INIT INFO

# Wait for appache2. Assumption: other (e.g. apache) still need some time
while (!(/etc/init.d/lighttpd status))
do
	sleep 1s 
done

tmux new -s pySocoLogger -d "python /home/pi/pySocoLogger/modbus.py"

exit 0
