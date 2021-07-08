#!/usr/bin/python3

import pigpio
from rotary_encoder import decoder
from math import log, pow, sin, tanh, pi
from dual_g2_hpmd_rpi import motors, MAX_SPEED
from time import sleep, time
import sys

m1Pos = 0
m2Pos = 0

# https://pinout.xyz/
M1_ENC1_PIN=4
M1_ENC2_PIN=17
M2_ENC1_PIN=18
M2_ENC2_PIN=27

STARTUP = 0
OPEN = 1
OPEN_HOLD = 2
CLOSE =  3
CLOSE_HOLD = 4

def m1Callback(way):
	global m1Pos
	m1Pos -= way

def m2Callback(way):
	global m2Pos
	m2Pos -= way

GPIO = pigpio.pi()
m1Decoder = decoder(GPIO, M1_ENC1_PIN, M1_ENC2_PIN, m1Callback)
m2Decoder = decoder(GPIO, M2_ENC1_PIN, M2_ENC2_PIN, m2Callback)

#------------------------------------------------------------------------
# shutdown procedure

def shutdown():
	motors.setSpeeds(0,0)
	motors.disable()
	m1Decoder.cancel()
	m2Decoder.cancel()
	GPIO.stop()

#------------------------------------------------------------------------
# helper functions

def constrain( _val, _min, _max):
	return min(_max, max(_min,_val))


def ease(_val, _target, _ease):
  return _ease * (_target - _val)

def sigmoid(_value, _function=-1):
	_value = constrain(_value, 0.0, 1.0)
	if _function == 0: # natural log
		return 1 / ( 1 + pow(-(12 * _value - 6)))
	elif _function == 1: # hyperbolic tan
		return 0.5 * tanh((2 * pi * _value) - pi) + 0.5
	elif _function == 2: # sine squared
		return pow(sin(0.5 * pi * _value), 2)
	else: # default to linear
		return _value

#------------------------------------------------------------------------
# main()

def main():
	cpr = 131*64
	motors.enable()
	motors.setSpeeds( 0, 0 )
	powerEasing=1
	power = 0
	powerLimit = 400
	powerScalar = 1
	sigmoidFunction=2
	targetOpen = cpr*2/3
	targetClose = 0
	target = 0
	tDuration = 10
	tEnd = tDuration
	tCurrent = 0
	tLast = 0
	progress = 0
	state = STARTUP # 0 = startup

	while True:
		tCurrent = time()

		if state == STARTUP:
			if tCurrent > tEnd:
				tEnd = tCurrent + tDuration
				state = OPEN
		elif state == OPEN:
			if tCurrent > tEnd:
				tEnd = tCurrent + tDuration
				state = OPEN_HOLD
				target = targetOpen
			else:
				progress = constrain(1-((tEnd - tCurrent) / (tDuration)),0,1)
				target = (sigmoid(progress,sigmoidFunction) * (targetOpen - targetClose)) + targetClose
		elif state == OPEN_HOLD:
			if tCurrent > tEnd:
				tEnd = tCurrent + tDuration
				state = CLOSE
		elif state == CLOSE:
			if tCurrent > tEnd:
				tEnd = tCurrent + tDuration
				state = CLOSE_HOLD
				target=targetClose
			else:
				progress = (tEnd - tCurrent) / tDuration
				target = (sigmoid(progress,sigmoidFunction) * (targetOpen - targetClose)) + targetClose
		elif state == CLOSE_HOLD:
			if tCurrent > tEnd:
				tEnd = tCurrent + tDuration
				state = OPEN

		
		force = powerScalar*(target - m1Pos)
		power += ease(power, force, powerEasing)
		power = constrain(power, -powerLimit, powerLimit)

		motors.setSpeeds(power,0)
		if motors.getFaults():
			break

		# if (tCurrent - tLast > 1):
		# 	print ("state: ", state," | power: ",power, " | target: ", target,"left encoder count: ",m1Pos," | right encoder count: ",m2Pos)
		# 	tLast=tCurrent

if __name__ == "__main__":
	try:
		main()
	except Exception as e:
		print("Exception: ",e)
	finally:
		shutdown()
		sys.exit()

