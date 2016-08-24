#!/usr/bin/python3

import time
import gc

# this very simple script will read from a 4 position switch
#


import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

PIN_A = 16
PIN_B = 19
PIN_C = 20
PIN_D = 26


GPIO.setup(PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_C, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_D, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# these functions return integers

state_A = 0 if GPIO.input(PIN_A) else 1
state_B = 0 if GPIO.input(PIN_B) else 1
state_C = 0 if GPIO.input(PIN_C) else 1
state_D = 0 if GPIO.input(PIN_D) else 1

start_time = time.time()

print( 'initial states: A {0} B {1} C {2} D {3}'.format( state_A, state_B, state_C, state_D ) )

while True:

# simple polling loop
	time.sleep(0.01)
#	gc.collect(1)

	changed = False

	new_A = 0 if GPIO.input(PIN_A) else 1
	new_B = 0 if GPIO.input(PIN_B) else 1
	new_C = 0 if GPIO.input(PIN_C) else 1
	new_D = 0 if GPIO.input(PIN_D) else 1

	if state_A != new_A:
		state_A = new_A
		changed = True
	if state_B != new_B:
		state_B = new_B
		changed = True
	if state_C != new_C:
		state_C = new_C
		changed = True
	if state_D != new_D:
		state_D = new_D
		changed = True

	if changed:
		if state_A :
			print('{0:.2f} A is now set '.format( time.time() ) );
		if state_B :
			print('{0:.2f} B is now set '.format( time.time() ) );
		if state_C :
			print('{0:.2f} C is now set '.format( time.time() ) );
		if state_D :
			print('{0:.2f} D is now set '.format( time.time() ) );



GPIO.cleanup()
