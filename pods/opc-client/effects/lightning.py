#!/usr/bin/env python

import random
import time

from effectlayer import EffectLayer

class Lightning(EffectLayer):
    '''
    An effect layer to add more responsive interactivity.  Simulate a lightning
    bolt fired from the lower to upper dodecahedron, flowing across the axon
    bridge.  Intended to be listed as the last layer in a playlist entry.  When
    a button is pressed and the lightning bolt is firing, the entire frame will
    be overwritten.  When not firing, the frame is passed through unchanged.

                                    -- mct, Wed Oct 28 16:48:53 PDT 2015
    '''

    # Number of LEDs in each section
    num_lower = 20
    num_axon  = 27
    num_upper = 50

    lower_offset = 0
    axon_offset  = 20
    upper_offset = 20+27

    # The formatting of the 'sequence' array below is pretty wonky, but it lets
    # us rapidly prototype patterns using ASCII.  The first element is the RGB
    # scalar for the lower dodeca, the second is an 27-byte long ASCII string
    # where each character represents one LED in the axon, the third is the RGB
    # scalar for the upper dodeca, and the last is a boolean indicating if this
    # frame should be frozen until the button is released.

    sequence = (
        # Starting on lower dodeca
        # Lightning flash across axon

        [ 0.0,   '     ______________________',   0.0, False ],
        [ 0.0,   '     ______________________',   0.0, False ],
        [ 0.0,   '     ______________________',   0.0, False ],
        [ 0.0,   '     ______________________',   0.0, False ],

        [ 1.0,   '     ______________________',   0.0, False ],
        [ 1.0,   '     ______________________',   0.0, False ],
        [ 1.0,   '     ______________________',   0.0, False ],

        [ 1.0,   '@    ______________________',   0.0, False ],
        [ 1.0,   '@@   ______________________',   0.0, False ],
        [ 1.0,   '@@@@ ______________________',   0.0, False ],
        [ 1.0,   '225@@@@@@__________________',   0.0, False ],
        [ 1.0,   '____225@@@@@@______________',   0.0, False ],
        [ 9.0,   '________225@@@@@@__________',   0.0, False ],
        [ 8.0,   '____________225@@@@@@______',   0.0, False ],
        [ 7.0,   '________________225@@@@@@__',   0.0, False ],
        [ 6.0,   '___________________225@@@@@',   0.0, False ],

        # Hitting upper dodeca
        [ 0.0,   '_____________________225@@@',   1.0, False ],
        [ 0.0,   '______________________225@@',   1.0, False ],
        [ 0.0,   '_______________________225@',   1.0, False ],
        [ 0.0,   '________________________225',   1.0, False ],
        [ 0.0,   '_________________________22',   1.0, False ],
        [ 0.0,   '__________________________1',   1.0, False ],

        [ 0.0,   '___________________________',   1.0, True ],
        [ 0.0,   '___________________________',   1.0, False ],
        [ 0.0,   '___________________________',   0.9, False ],
        [ 0.0,   '___________________________',   0.8, False ],
        [ 0.0,   '___________________________',   0.7, False ],
        [ 0.0,   '___________________________',   0.6, False ],

        # Blanking afterwards
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
        [ 0.0,   '___________________________',   0.0, False ],
    )

    # First element is the color of the lower dodeca, second is the upper
    dodeca_colors = [
            (( 255,   0, 255 ), ( 255, 255,   0 )),
            ((   0, 255,   0 ), ( 255,   0, 255 )),
            ((   0,   0, 255 ), ( 255, 255,   0 )),
            (( 255,   0,   0 ), (   0, 255,   0 )),
            ((   0, 255,   0 ), ( 255,   0,   0 )),
        ]

    def __init__(self):
        self.armed = False
        self.firing = False
        self.index = 0
        self.pause_time = 0

    def render(self, model, params, frame):
        button = True in params.buttonState

        if not self.armed and not button:
            self.armed = True
            print "Lightning: Armed"

        if self.armed and not self.firing and button:
            print "Lightning: Firing"
            self.firing = True
            self.armed = False
            self.index = 0
            self.pause_time = 0

            self.dodeca_colors.insert(0, self.dodeca_colors.pop())

            print repr(self.dodeca_colors[0])

            self.r1, self.g1, self.b1 = self.dodeca_colors[0][0]
            self.r2, self.g2, self.b2 = self.dodeca_colors[0][1]

        if not self.firing:
            return

        lower_color, axon_string, upper_color, pause = self.sequence[self.index]

        for i in range(self.num_lower):
            frame[self.lower_offset + i] = (self.r1 * lower_color, self.g1 * lower_color, self.b1 * lower_color)

        for i in range(self.num_upper):
            frame[self.upper_offset + i] = (self.r2 * upper_color, self.g2 * upper_color, self.b2 * upper_color)

        for i, value in enumerate(axon_string):
            r, g, b = (255, 255, 255)

            if   value in ('@', 'W'): frame[self.axon_offset + i] = (r,     g,     b    )
            elif value in ('1',    ): frame[self.axon_offset + i] = (r*.1,  g*.1,  b*.1 )
            elif value in ('2',    ): frame[self.axon_offset + i] = (r*.2,  g*.2,  b*.2 )
            elif value in ('3',    ): frame[self.axon_offset + i] = (r*.3,  g*.3,  b*.3 )
            elif value in ('4',    ): frame[self.axon_offset + i] = (r*.4,  g*.4,  b*.4 )
            elif value in ('5',    ): frame[self.axon_offset + i] = (r*.5,  g*.5,  b*.5 )
            elif value in ('6',    ): frame[self.axon_offset + i] = (r*.6,  g*.6,  b*.6 )
            elif value in ('7',    ): frame[self.axon_offset + i] = (r*.7,  g*.7,  b*.7 )
            elif value in ('8',    ): frame[self.axon_offset + i] = (r*.8,  g*.8,  b*.8 )
            elif value in ('9',    ): frame[self.axon_offset + i] = (r*.9,  g*.9,  b*.9 )
            elif value in ('R',    ): frame[self.axon_offset + i] = (255,   0,   0)
            elif value in ('G',    ): frame[self.axon_offset + i] = (  0, 255,   0)
            elif value in ('B',    ): frame[self.axon_offset + i] = (  0,   0, 255)
            else:                     frame[self.axon_offset + i] = (  0,   0,   0)

        # Scale from [0..255] to [0..1]
        for i in range(len(frame)):
            for j in range(len(frame[i])):
                frame[i][j] /= 255.0

        # If they haven't released the button yet, freeze specific frames, but
        # only for up to N seconds.
        if pause and not self.armed:
            if not self.pause_time:
                print "Lightning: Paused"
                self.pause_time = time.time()

            if time.time() - self.pause_time <= 3:
                return
            else:
                print "Lightning: Pause max"

        self.index += 1
        if self.index >= len(self.sequence):
            self.firing = False
            print "Lightning: Done firing"
