#!/bin/bash
#
RETVAL=0;

start() {
    echo "Starting Wifi data collection"
    SEARCH=`ps acx | grep listae.py`
    if [ -z "$SEARCH" ]; then
       exec /opt/wifi/listae.py > /dev/null &
    fi
    if [ ! -z "$SEARCH" ]; then
       echo "Already running!" 
    fi
}

stop() {
    echo "Stopping wifi data collection"
    killall listae.py
}

restart() {
stop
start
}

case "$1" in
start)
  start
;;
stop)
  stop
;;
restart)
  restart
;;
*)

echo "Usage: $0 {start|stop|restart}"
exit 1
esac

exit $RETVAL  
