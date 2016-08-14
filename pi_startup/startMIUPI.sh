#!/bin/bash
#
# This script is meant to be the startup for a MIU raspberry pi.
#
# It will start two instances of the interface for the BPM monitor.
# Also control LED's for backpack.
#
# Assumptions: NONE use global paths.
#

echo starting MIU PI on `hostname`

HOME=/home/flaming
BPMMON=$HOME/pulse/BPM/PulsePolarBPM

PODID=`cat /etc/pod.id`
IP=192.168.1.255
PORT=5000
LOG=/var/log/miu.log

$HOME/pulse/pi_startup/cycleLogs.sh $LOG

# The program now knows how to handle 0,1,or 2 connected sensors.
stdbuf -oL $BPMMON -i$PODID -a$IP -p$PORT >& $LOG &

# start LED backpack LED's.

