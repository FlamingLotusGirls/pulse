from effectlayer import EffectLayer
import numpy
import time


class Speck(EffectLayer):
	def __init__(self, color, index=0):
		self.index = index
		self.color = numpy.array(color)
		self.lifespan = 3.5
		self.lastSwitch = time.time()

	def render(self, model, params, frame):
		if self.index < model.numLEDs: # if it's still alive...

			frame[self.index] = self.color;

			# advance the index if enough time has elapsed
			if (params.time > self.lastSwitch + self.lifespan/model.numLEDs):
				self.index = self.index + 1
				self.lastSwitch = params.time


class SpeckLayer(EffectLayer):
	def __init__(self, button = 0, color = [1,1,1]):
		self.specks = [] # currently active specks
		self.color = color
		self.button = button # which button triggers specks (if you want both buttons, add 2 layers!)

		self.lastButtonState = False
		self.lastSwitch = time.time()
		self.rateLimit = 1. # minimum inter-speck interval if button is held down

	def render(self, model, params, frame):

		# start a new speck if the button has just been depressed or has been down for longer
		# than the rate limit
		buttonState = params.buttonState[self.button]
		if buttonState:
			if not self.lastButtonState or params.time > self.lastSwitch + self.rateLimit:
				self.lastSwitch = params.time
				self.specks.append(Speck(self.color))

		self.lastButtonState = buttonState

		# render specks, and remove dead ones from the list
		deadspecks = []
		for speck in self.specks:
			speck.render(model, params, frame)
			if speck.index > model.numLEDs: # if it's gone through all the indices, it's dead
				deadspecks.append(speck)

		for speck in deadspecks:
			self.specks.remove(speck)


