import math
import random
import numpy
from effectlayer import *

class RandomBlinkCycleLayer(EffectLayer):

    def __init__(self, model):
        self.frequency = 0.15
        self.phase = [0]*model.numLEDs
        for i in range(model.numLEDs):
            self.phase[i] = random.random()
        self.color = numpy.array((1.0, 1.0, 1.0))
        self.randomness = 0.2

    def render(self, model, params, frame):
        for i in range(model.numLEDs):
            self.color[0] = random.random()
            self.color[1] = random.random()
            self.color[2] = random.random()
            frame[i] += self.color * (math.sin(math.pi*(params.time*self.frequency)))**2


