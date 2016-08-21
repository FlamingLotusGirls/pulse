import time
import numpy as np
import random
from util import randomColor, hsvColorAdd
from effectlayer import EffectLayer
from colorsys import hsv_to_rgb, rgb_to_hsv

class HolidayColorWiper(EffectLayer):
    """
    Wipes between some number of specific colors.
    Without the optional parameters, this behaves identically to
    the ColorWiper layer.

    Optional Constructor parameters:
    - colors: an array of three-element decimal color spefiers in the
      range 0-255).
    - timers: A timer parameter in seconds, which determines the time to wait
      before automatically switching colors
    """
    def __init__(self, model, colors=None, timer=None):
        self.model = model
        self.wipeDuration = 1
        self.hueDelta = .27 # add this to the hue on each transition
        self.buttonDown = False
        self.wipeStartTime = None # should be None if no wipe is in progress
        self.change_every = timer
        self.colorPalette = [np.array(color) / 255.0 for color in colors]
        self.color = self.getColor()
        self.resetTimer()
        self.oldColor = None # ""

    def resetTimer(self):
        self.changeTime = time.time()

    def time_since_change(self):
        return time.time() - self.changeTime

    def getColor(self):
        if self.colorPalette:
            idx = random.randrange(0, len(self.colorPalette))
            self.color_idx = idx
            return self.colorPalette[idx]
        else:
            return randomColor()

    def nextColor(self):
        """ If a color palette is set, move to the next color in the palette,
            otherwise, move around the color wheel by self.hueDelta
        """
        if self.colorPalette:
            self.color_idx = (self.color_idx + 1) % len(self.colorPalette)
            return self.colorPalette[self.color_idx]
        else:
            return hsvColorAdd(self.color, (self.hueDelta, 0, 0))


    def startWipe(self):
        self.wipeStartTime = time.time()
        self.oldColor = self.color
        self.color = self.nextColor()


    def setWipeStateFromButtons(self, params):
        """ if we detect a new button-press and aren't already in the middle of a wipe,
        set a new color and make the current color the old color """
        if (params.buttonState[0] or params.buttonState[1]):
            if not self.buttonDown and not self.wipeStartTime:
                self.buttonDown = True
                self.startWipe()
        else:
            self.buttonDown = False

    def setWipeStateFromTimer(self):
        if self.change_every:
            if self.time_since_change() >= self.change_every:
                self.startWipe()
                self.resetTimer()

    def wipePercentCompleted(self):
        if self.wipeStartTime is not None:
            return (time.time() - self.wipeStartTime) / self.wipeDuration
        else:
            return 1

    def render(self, model, params, frame):
        self.setWipeStateFromButtons(params)
        self.setWipeStateFromTimer()
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