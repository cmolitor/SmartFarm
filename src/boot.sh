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

# Add to file "/etc/rc.local" the path to this file (e.g.: /home/pi/SmartFarm/src/boot.sh)

while (!(/etc/init.d/lighttpd status))
do
	sleep 1s
	date >> /home/pi/SmartFarm/test.txt 
done

# sleep 10s
# tmux new-session -s pySocoLogger -d "python /home/pi/SmartFarm/src/modbus.py"
# echo "Starting tmux session"
sleep 20s
tmux new-session -s pysoco -d
tmux send-keys -t pysoco:0 "cd /home/pi/SmartFarm/src" C-m
tmux send-keys -t pysoco:0 "python /home/pi/SmartFarm/src/modbus.py" C-m

exit 0
