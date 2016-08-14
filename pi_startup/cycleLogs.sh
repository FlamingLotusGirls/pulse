#!/bin/bash

LOG=$1

for i in 4 3 2 1; do
	[ -f $LOG.$i ] && mv $LOG.$i $LOG.$((i+1))
done

[ -f $LOG ] && mv $LOG $LOG.1

