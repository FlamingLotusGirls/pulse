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

PODID=`cat /etc/pod.id`

echo starting HEART PI on `hostname`

python $CONTROL &

