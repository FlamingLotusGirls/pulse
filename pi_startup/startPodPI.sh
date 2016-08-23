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
OPCSERVER=$HOME/fadecandy/bin/fcserver-rpi

BPMLOG=/var/log/pod.log
SOUNDLOG=/var/log/sound.log
OPCLOG=/var/log/opc_server.log
LEDLOG=/var/log/opc_client.log

CYCLELOGS=$HOME/pulse/pi_startup/cycleLogs.sh

$CYCLELOGS $BPMLOG
$CYCLELOGS $SOUNDLOG
$CYCLELOGS $OPCLOG
#$CYCLELOGS $LEDLOG

# start BPM monitor. Need to background this.
stdbuf -oL $BPMMON -i$PODID -a$IP -p$PORT >& $BPMLOG &

# start OPC server
stdbuf -oL $OPC_SERVER $OPC_CONFIG >& $OPC_LOG &

# start LED monitor... background.

# start audio ...
stdbuf -oL $SOUND -i$PODID >& $SOUNDLOG &


