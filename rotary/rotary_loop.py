#!/usr/bin/python3

import time
import gc

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

PIN_A = 22
PIN_B = 23


GPIO.setup(PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# these functions return integers

state_A = GPIO.input(PIN_A)
state_B = GPIO.input(PIN_B)
old_state = 0
incr = 0
value = 0
clicks = 0
start_time = time.time()

print( " type: " + str(type(state_A)) )

print( "initial states: A " + str(state_A) + " B " + str(state_B) )

while True:
	time.sleep(0.001)
#	gc.collect(1)
	changed = False
	new_A = GPIO.input(PIN_A)
	new_B = GPIO.input(PIN_B)
	if state_A != new_A:
		state_A = new_A
		changed = True
	if state_B != new_B:
		state_B = new_B
		changed = True

	if changed:
		incr = incr + 1
#		state_C = state_A ^ state_B
#		new_state = ( state_A * 4 ) + ( state_B * 2 ) + state_C
		new_state = ( state_A  ^ state_B ) | ( state_B << 1 )
		delta = (new_state - old_state) % 4

		c_changed = False
		if  delta == 1 :
			value = value + 1
			if (value >> 2) != clicks:
				clicks = value >> 2
				c_changed = True
		elif delta == 3 :
			value = value - 1
			if (value >> 2) != clicks:
				clicks = value >> 2
				c_changed = True

		if c_changed:
			print( '{0:.2f} delta: {1} value: {2}'.format( time.time() - start_time, delta, (value >> 2 ) ) )

		old_state = new_state


GPIO.cleanup()
