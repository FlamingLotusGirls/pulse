import math
import random
import numpy
from effectlayer import *

class ColorCycleLayer(EffectLayer):

    def __init__(self, hueSpeed=0.00003, saturationSpeed=0.0005):
        self.hueSpeed = hueSpeed
        self.saturationSpeed = saturationSpeed
        self.hue = 0
        self.saturation = 1

    def render(self, model, params, frame):
        self.hue = self.increment(self.hue, self.hueSpeed)
        self.saturation = self.increment(self.saturation, self.saturationSpeed)
        color = numpy.array(colorsys.hsv_to_rgb(self.hue, math.sin(math.pi*self.saturation)**2, 1))
        frame[:] *= color

    def increment(self, value, step):
        value += step
        if value>1:
            value -= 1
        return value