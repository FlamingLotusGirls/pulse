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

# TODO - figure out how to pick different BPM monitors.

# start 1st BPM monitor.
$BPMMON -i$PODID -a$IP -p$PORT > /var/log/miuS1.log &

# start 2nd BPM monitor.
$BPMMON -i$PODID -a$IP -p$PORT > /var/log/miuS2.log &

# start LED backpack LED's.

