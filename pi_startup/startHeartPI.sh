#!/bin/bash
#
# This script is meant to be the startup for the HEART raspberry pi.
#
# It will start the listener to the BPM on the network for flipping 
# fire solendoids.
#
# Assumptions: NONE! use global paths ...
#

SRCDIR=/home/flaming
CONTROL=$SRCDIR/pulse/network/heartbeat_controller.py
DMX=$SRCDIR/pulse/dmx/dmx_controller.py

PODID=`cat /etc/pod.id`
HB_LOG=/var/log/heart.log
DMX_LOG=/var/log/dmx.log

$SRCDIR/pulse/pi_startup/cycleLogs.sh $HB_LOG
$SRCDIR/pulse/pi_startup/cycleLogs.sh $DMX_LOG

echo starting HEART PI on `hostname` > $HB_LOG

stdbuf -oL python $CONTROL $PODID >> $HB_LOG 2>&1 &

echo starting DMX PI on `hostname` > $DMX_LOG

stdbuf -oL python $DMX $PODID >> $DMX_LOG 2>&1 &
 
