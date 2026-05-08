#!/bin/bash
# Restart wrapper — keeps pi-egt running after any crash or in-app restart.
sleep 8
cd /home/pi/pi-egt
while true; do
    DISPLAY=:0 python3 main.py >> /tmp/pi_egt.log 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S') pi-egt exited (code $?), restarting in 3s" >> /tmp/pi_egt.log
    sleep 3
done
