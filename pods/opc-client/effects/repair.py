#!/usr/bin/env python

from effectlayer import EffectLayer

class Repair(EffectLayer):
    '''
    An effect layer to work around some broken LEDs on the sculpture which
    have lost one of their color channels.  If we were about to set an LED to
    a color which has a component made up of a missing color channel, disable
    that LED entirely for this frame.  Otherwise, don't change the LED,
    allowing it to display any colors it is capable of.

    This layer should be run on every single pattern as the very last layer.

                                    -- mct, Thu Nov  5 19:51:02 PST 2015
    '''

    # Set to None to disable debugging, or set to a color tuple to turn the
    # entire sculpture that color when a button is pressed.  For example, to
    # easily spot LEDs which are missing either the Red or Green channel, set
    # debug_color to (1, 1, 0)

    #debug_color = (1, 1, 1)
    #debug_color = (1, 1, 0)
    #debug_color = (0, 1, 1)
    #debug_color = (1, 0, 1)
    debug_color = None

    def __init__(self):
        pass

    def render(self, model, params, frame):
        if self.debug_color and True in params.buttonState:
            for i in range(model.numLEDs):
                frame[i] = self.debug_color
            print "repair: Set", params.buttonState, "LEDs to", repr(self.debug_color)

        # 38 is missing red
        if frame[38][0] > 0.0:
            frame[38] = (0, 0, 0)

        # 89 is missing green
        if frame[89][1] > 0.0:
            frame[89] = (0, 0, 0)

        # 53 is broken.  It turns on for a fraction of a second, then goes
        # dark.  Might be a bad regulator, going into thermal protection?
        # Just disable it entirely for now.
        frame[53] = (0, 0, 0)
