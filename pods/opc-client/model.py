import json
import numpy

class Model(object):
    """
    Minimal base class for a model describing the layout of the LEDs in physical space. 
    """
    def __init__(self, num_leds):
        self.numLEDs = num_leds
