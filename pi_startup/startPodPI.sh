#!/bin/bash
#
# This script is meant to be the startup for a POD raspberry pi.
#
# It will start the POD LED driver,
# sounds module, and the attached BPM monitor.
#

echo starting POD PI on `hostname`

HOME=/home/flaming
BPMMON=$HOME/pulse/BPM/PulsePolarBPM

PODID=`cat /etc/pod.id`
IP=192.168.1.255 # broadcast.
PORT=5000

# start BPM monitor. Need to background this.
$BPMMON -i$PODID -a$IP -p$PORT &

# start LED monitor... background.

# start audio sensor ...

