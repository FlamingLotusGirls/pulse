import time
import os
import sys
import effectlayer

class InputGetter:
    def update(self, effectparams):
        pass


# Crappy curses-based keyboard button emulator. See init method for key codes.
class KeyboardInputGetter(InputGetter):
    def __init__(self, screen):
        # curses stuff...
        import curses
        screen.nodelay(True) # make getch calls non-blocking
        self.screen = screen

        self.buttonDownKeys = ["d", "k"]
        self.buttonUpKeys = ["e", "i"]
        self.cachedTimes = [0, 0] # time that the button was pressed down or released

        for i in range(len(self.buttonDownKeys)):
            print("Button #%i down/up: %s/%s" % (i, self.buttonDownKeys[i], self.buttonUpKeys[i]))

    def update(self, effectparams):
            # get a character from the curses screen
            char = self.screen.getch()
            try:
                char = chr(char)
            except:
                pass

            for i in range(len(self.buttonDownKeys)):
                # update button-down times stored in this object
                if char == self.buttonDownKeys[i] and effectparams.buttonState[i] != True:
                    effectparams.buttonState[i] = True
                    self.cachedTimes[i] = time.time()
                elif char == self.buttonUpKeys[i] and effectparams.buttonState[i] != False:
                    effectparams.buttonState[i] = False
                    self.cachedTimes[i] = time.time()

                effectparams.buttonTimeSinceStateChange[i] = time.time() - self.cachedTimes[i]

