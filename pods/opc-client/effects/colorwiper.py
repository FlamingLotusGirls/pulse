import time
import numpy as np
from util import randomColor, hsvColorAdd
from effectlayer import EffectLayer
from colorsys import hsv_to_rgb, rgb_to_hsv

class ColorWiper(EffectLayer):
    def __init__(self, model):
        self.model = model
        self.wipeDuration = 1
        self.hueDelta = .27 # add this to the hue on each transition
        self.buttonDown = False
        self.wipeStartTime = None # should be None if no wipe is in progress
        self.color = randomColor()
        self.oldColor = None # ""

    def setWipeStateFromButtons(self, params):
        """ if we detect a new button-press and aren't already in the middle of a wipe,
        set a new color and make the current color the old color """
        if (params.buttonState[0] or params.buttonState[1]):
            if not self.buttonDown and not self.wipeStartTime:
                self.buttonDown = True
                self.wipeStartTime = time.time()
                self.oldColor = self.color
                self.color = hsvColorAdd(self.color, (self.hueDelta, 0, 0))
        else:
            self.buttonDown = False

    def wipePercentCompleted(self):
        if self.wipeStartTime is not None:
            return (time.time() - self.wipeStartTime) / self.wipeDuration
        else:
            return 1

    def render(self, model, params, frame):
        self.setWipeStateFromButtons(params)
        percentDone = self.wipePercentCompleted()

        # if the wipe is complete, clear its state so another wipe can be initiated
        if percentDone >= 1:
            self.oldColor = None
            self.wipeStartTime = None

        for i in range(self.model.numLEDs):
            if self.oldColor is not None and 1-self.model.nodes[i,1] > percentDone:
                color = self.oldColor
            else:
                color = self.color
            frame[i] = color