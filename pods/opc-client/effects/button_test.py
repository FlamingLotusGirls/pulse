import math
import random
import numpy
from effectlayer import *

class ButtonTestLayer(EffectLayer):

    def __init__(self):
        self.buttonZeroColor = 0
        self.buttonOneColor = .25
        self.noButtonColor = .5
        self.bothButtonsColor = .75

    def render(self, model, params, frame):
        if not params.buttonState[0] and not params.buttonState[1]:
            color = numpy.array(colorsys.hsv_to_rgb(self.noButtonColor,1,1))
        elif params.buttonState[0] and params.buttonState[1]:
            color = numpy.array(colorsys.hsv_to_rgb(self.bothButtonsColor,1,1))
        elif params.buttonState[0]:
            color = numpy.array(colorsys.hsv_to_rgb(self.buttonZeroColor,1,1))
        else:
            color = numpy.array(colorsys.hsv_to_rgb(self.buttonOneColor,1,1))
        frame[:] += color
