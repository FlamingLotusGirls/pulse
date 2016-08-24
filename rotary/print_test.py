#!/usr/bin/python3

import time
import sys

while True:
	print( '{0:.2f} is now '.format(time.time()), flush=True)
#	sys.stdout.flush()
	time.sleep(0.5)
