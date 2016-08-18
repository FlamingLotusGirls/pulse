import time
from threading import Thread
import sys
from InputGetter import *

class PlaylistAdvanceThread(Thread):
    """
    Advances the active playlist periodically.
    """
    def __init__(self, renderer, switchInterval):
        Thread.__init__(self)
        self.daemon = True
        self.renderer = renderer
        self.switchInterval = switchInterval

    def run(self):
        lastActive = time.time()
        while True:
            if time.time() - lastActive > self.switchInterval:
                self.renderer.advanceCurrentPlaylist()
                lastActive = time.time()
            time.sleep(1)


class KeyboardMonitorThread(Thread):
    def __init__(self, params, screen):
        Thread.__init__(self)
        self.daemon = True
        self.params = params
        self.getter = KeyboardInputGetter(screen)
        self.buttonGetter = ButtonInputGetter()

    def run(self):
        while True:
            self.getter.update(self.params)
            self.buttonGetter.update(self.params)
            time.sleep(0.05)

class ButtonMonitorThread(Thread):
    def __init__(self, params):
        Thread.__init__(self)
        self.daemon = True
        self.params = params
        self.buttonGetter = ButtonInputGetter()

    def run(self):
        while True:
            self.buttonGetter.update(self.params)
            time.sleep(0.05)
