#!/bin/bash
#
# This script is meant to be the startup for a POD raspberry pi.
#
# It will start the POD LED driver,
# sounds module, and the attached BPM monitor.
#

echo starting POD PI on `hostname`

PODID=`cat /etc/pod.id`
IP=192.168.1.255 # broadcast.
PORT=5000

HOME=/home/flaming
BPMMON=$HOME/pulse/BPM/PulsePolarBPM
SOUND=$HOME/pulse/audio/sound_test

# start BPM monitor. Need to background this.
$BPMMON -i$PODID -a$IP -p$PORT >& /var/log/pod.log &

# start LED monitor... background.

# start audio ...
$SOUND -i$PODID >& /var/log/sound.log &


