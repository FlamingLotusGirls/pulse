import math
import random
import numpy as np
from util import hsvColorAdd, jitter, colorJitter
from effectlayer import EffectLayer 
from colorsys import hsv_to_rgb, rgb_to_hsv

CENTER_FREQ = 0.6 #Hz

def mutateColor(color, hue_jitter=0.1, sat_jitter=0.5, val_jitter=0.5):
    return hsvColorAdd(color, colorJitter(hue_jitter, sat_jitter, val_jitter) )



class ColorWave(EffectLayer):
    def __init__(self, model, grayscale=False):
        self.model = model
        self.phases = [ random.random() for i in range(self.model.numLEDs) ]
        self.frequencies = [CENTER_FREQ + jitter(0.05) for i in range(self.model.numLEDs) ]
        if grayscale:
            self.color = np.array([1,1,1])
        else:
            self.color = np.array([ random.random() for i in range(3) ])
        self.colors = [ mutateColor(self.color, sat_jitter=0) for i in range(self.model.numLEDs)]

    def render(self, model, params, frame):

        for i in range(len(self.phases)):
            # self.phases[i] += jitter()
            self.frequencies[i] += jitter(0.00000000001)

        for i in range(self.model.numLEDs):
            # color = mutateColor(self.colors[i], 0, 0.005, 0)
            color = self.colors[i]
            frame[i] = color * (math.sin(math.pi*(params.time*self.frequencies[i] + self.phases[i])))**2

