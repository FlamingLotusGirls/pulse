#!/bin/bash
#
# This script is meant to be the startup for a MIU raspberry pi.
#
# It will start the POD LED driver,
# sounds module, and the attached BPM monitor.
#
# Assumptions: This script lives 
#

echo starting POD PI on `hostname`

HOME=/home/flaming
BPMMON=$HOME/BPM/PulsePolarBPM

PODID=`cat /etc/pod.id`

# TODO - figure out how to pick different BPM monitors.

# start 1st BPM monitor.
$BPMMON -i $PODID

# start 2nd BPM monitor.
$BPMMON -i $PODID

# start LED backpack.

