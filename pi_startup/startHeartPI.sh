#!/bin/bash
#
# This script is meant to be the startup for a POD
# raspberry pi. It will start the POD LED driver,
# sounds module, and the attached BPM monitor.
#
# Assumptions: This script lives
#
#

SRCDIR=/home/flaming
BPMMON=$SRCDIR/pulse/BPM/PulsePolarBPM
CONTROL=$SRCDIR/pulse/network/heartbeat_controller.py

PODID=`cat /etc/pod.id`

echo starting HEART PI on `hostname`

python $CONTROL &


