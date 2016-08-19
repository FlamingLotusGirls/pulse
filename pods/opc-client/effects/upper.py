import math
import random
import numpy

from effectlayer import *

class UpperLayer(EffectLayer):

    def __init__(self, hue=16/float(360)):
        self.hue = hue

    def render(self, model, params, frame):
        len = frame.size/3
        myfloat = 16/float(360)
        # iterate through pixels...
        for i in range(0,len):
            if i in model.upperIndices:
                frame[i] = 1.0  # white
            else:
                frame[i] = 0.0  # black
                
