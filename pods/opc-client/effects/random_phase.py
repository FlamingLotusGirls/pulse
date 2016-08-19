import math
import random
import numpy
from effectlayer import *

class RandomPhaseLayer(EffectLayer):

    def __init__(self, model):
        self.frequency = 0.5 # base frequency of blinking in Hz
        self.period = 2  # seconds
        self.phase = [0]*model.numLEDs
        for i in range(model.numLEDs):
            self.phase[i] = random.random()
        self.color = numpy.array((1, 1, 1))
        self.lowerRandomness = 1
        self.upperRandomness = 1
        self.axonOn = False
        self.lifecycle = "start"
        self.chaseBlinks = -1


    def render(self, model, params, frame):
        self.axonOn = False
        if self.lifecycle == "start":
            if params.buttonState[0] or params.buttonState[1]:
                self.lifecycle = "buttonDown"
                print "button down!"
            else:
                self.upperRandomness = 1
                self.lowerRandomness = 1
        
        if self.lifecycle == "buttonDown":
            if not (params.buttonState[0] or params.buttonState[1]):
                self.lifecycle = "decay"
                print "button back up!"
            else:
                self.upperRandomness = 1
                self.lowerRandomness -= 0.005
                if self.lowerRandomness < 0:
                    self.lowerRandomness = 0
                    self.lifecycle = "chase"
                    print "starting chase!"
                    self.cachedTime = params.time

        if self.lifecycle == "chase":
            self.lowerRandomness = 0
            # synchronize start of chase cycle with minimum intensity of lower dodeca
            lowerDodecaCyclePosition = (params.time % self.period)
            if self.chaseBlinks < 0:
                if lowerDodecaCyclePosition < 0.5:
                    print "chase ready!"
                    self.chaseBlinks = 0
            elif self.chaseBlinks == 0:
                if lowerDodecaCyclePosition > 0.5:
                    self.cachedTime = params.time
                    print "launch the chase!"
                    self.chaseBlinks = 1
            elif self.upperRandomness > 0:
                self.axonOn = True
                self.upperRandomness -= 0.002
            else:
                self.lifecycle = "end"
                self.cachedTime = params.time

        if self.lifecycle == "end": 
            self.upperRandomness = 0
            self.lowerRandomness = 0
            if params.time - self.cachedTime > 3*self.period:
                self.lifecycle = "decay"
        
        if self.lifecycle == "decay":
            self.upperRandomness += 0.002
            if self.upperRandomness > 1:
                self.upperRandomness = 1
            self.lowerRandomness += 0.002
            if self.lowerRandomness > 1:
                self.lowerRandomness = 1

            if self.upperRandomness == 1 and self.lowerRandomness == 1:
                self.lifecycle = "start"
        
        self.computeAxonValues(params.time, self.axonOn, model.axonIndices, frame)
        self.computeDodecaValues(params.time, self.lowerRandomness, model.lowerIndices, frame)
        self.computeDodecaValues(params.time, self.upperRandomness, model.upperIndices, frame)

    def computeDodecaValues(self, time, randomness, indices, frame): 
        for i in indices:
            frame[i] = self.color * (math.sin(math.pi*(time*self.frequency + randomness*self.phase[i])))**2

    def computeAxonValues(self, time, axonOn, indices, frame):
        if axonOn:
            for i in indices:
                frame[i] = self.color * (math.sin(math.pi*(time*self.frequency)))**2

        
