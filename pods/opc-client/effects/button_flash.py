import numpy
from effectlayer import *

class ButtonFlash(EffectLayer):

    def __init__(self, model):
        self.colors = [
            numpy.array((0.18, 0.3, 0.35)),
            numpy.array((0.4, 0.4, 0.0)),
            numpy.array((1, 1, 1))
        ]

        self.axon = model._getAxonIndices()

    def render(self, model, params, frame):
        #indices = model.axonIndices
        indices = range(len(frame))
	
        if params.buttonState[0]:
            for i in indices:
                frame[i] += self.colors[0]

        if params.buttonState[1]:
            for i in indices:
                frame[i] += self.colors[1]
            
        if params.buttonState[0] and params.buttonState[1]:
            for i in indices:
                frame[i] += self.colors[2]

