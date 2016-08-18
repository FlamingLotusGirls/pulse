#import math
#import random
import numpy
from effectlayer import *

class ButtonFlash(EffectLayer):

    def __init__(self, model):
        self.colors = [
            numpy.array((0.8, 0.3, 0.1)),
            numpy.array((0.4, 0.8, 0.0)),
            numpy.array((1, 1, 1))
        ]

        self.axon = model._getAxonIndices()
	self.lastButtonState = [False, False]
	self.timer = [0, 0]
	self.fadeTime = 0.300 #attack fade time on each button press

    def render(self, model, params, frame):
        #indices = model.axonIndices
        indices = range(len(frame))

        for button in [0,1]:
            buttonState = params.buttonState[button]
            if buttonState != self.lastButtonState:
                print "BRAAAAAAP!"
                self.timer[button] = params.time + self.fadeTime
            if params.time <= self.timer[button]:
                fadeDegree = (self.timer[button] - params.time) / self.fadeTime
                print "Time %f --> fade %f" % (self.timer[button]-params.time, fadeDegree)
            else:
                fadeDegree = int(buttonState) # peg to 0 or 1
            if not buttonState:
                fadeDegree = 1 - fadeDegree
#            if all(params.buttonState):
#                color = self.colors[2] * fadeDegree
#            else:
            print "%f --> %f (delta: %f)" % (params.time, self.timer[button], self.timer[button]-params.time)
            #print "%d: %f" % (button, fadeDegree)
            color = self.colors[button] * fadeDegree
            for i in indices:
                frame[i] += color

            self.lastButtonState[button] = buttonState

#        if params.buttonState[0]:
#            for i in indices:
#                frame[i] = self.colors[0]
#
#        if params.buttonState[1]:
#            for i in indices:
#                frame[i] = self.colors[1]
#            
#        if params.buttonState[0] and params.buttonState[1]:
#            for i in indices:
#                frame[i] = self.colors[2]

