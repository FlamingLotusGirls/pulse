import math
import random
import numpy
from colorsys import hsv_to_rgb, rgb_to_hsv

from effectlayer import *

class MonoLayer(EffectLayer):

    # nb - 16 degrees is the hue for giants orange. Looks a little red to me.
    def __init__(self, hue=30/float(360)):
        self.hue = hue

    def render(self, model, params, frame):
        len = frame.size/3
        for i in range(0,len):
            pixel = frame[i]
            hsv = numpy.array(rgb_to_hsv(pixel[0], pixel[1], pixel[2]))
            frame[i] = numpy.array(hsv_to_rgb(self.hue, (hsv[1]+0.5) / 1.5, hsv[2]))
            
