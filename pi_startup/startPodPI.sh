#!/bin/bash
#
# This script is meant to be the startup for a POD
# raspberry pi. It will start the POD LED driver,
# sounds module, and the attached BPM monitor.
#

echo starting POD PI on `hostname`

HOME=/home/flaming
BPMMON=$HOME/BPM/PulsePolarBPM

PODID=`cat /etc/pod.id`

# start BPM monitor. Need to background this.
$BPMMON -i $PODID &

# start LED monitor... background.

# start audio sensor ...

