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
SOUND=$HOME/pulse/audio/pulse_sound
OPC_SERVER=$HOME/fadecandy/bin/fcserver-rpi
OPC_CONFIG=$HOME/pulse/pi_startup/pulse_fc-config.json
POD_LED=$HOME/pulse/bin/pod.py

BPMLOG=/var/log/bpm.log
SOUNDLOG=/var/log/sound.log
OPCLOG=/var/log/opc_server.log
LEDLOG=/var/log/led.log

CYCLELOGS=$HOME/pulse/pi_startup/cycleLogs.sh

$CYCLELOGS $BPMLOG
$CYCLELOGS $SOUNDLOG
$CYCLELOGS $OPCLOG
$CYCLELOGS $LEDLOG

# start BPM monitor. Need to background this.
stdbuf -oL $BPMMON -i$PODID -a$IP -p$PORT >& $BPMLOG &

# start OPC server
stdbuf -oL $OPC_SERVER $OPC_CONFIG  &

# start LED code 
stdbuf -oL $POD_LED $PODID >& $LEDLOG &

# start audio ...
stdbuf -oL $SOUND -i$PODID >& $SOUNDLOG &


