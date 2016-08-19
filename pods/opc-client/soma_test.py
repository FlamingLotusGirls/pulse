#!/usr/bin/env python
from model import SomaModel
from renderer import Renderer
from controller import AnimationController
from effectlayer import *
from effects.firefly_swarm import *
from effects.color_cycle import *
from effects.button_test import *
from effects.random_phase import *
from effects.random_blink_cycle import *
from effects.chase import AxonChaseLayer
from effects.colorwave import ColorWave
from effects.colorwiper import ColorWiper
from effects.holidaycolorwiper import HolidayColorWiper
from effects.invert import InvertColorsLayer, InvertColorByRegionLayer
from effects.color_palette_battle import *
from effects.photo_colors import *
from effects.dim_bright_button_layer import *
from effects.specklayer import *
from playlist import Playlist
from threads import PlaylistAdvanceThread, KeyboardMonitorThread
from random import random
from math import *
import os
import sys


# Just a test to make sure that I can reference sections of the new model
class SomaTestLayer(EffectLayer):
    lower = True
    def render(self, model, params, frame):
        if random() > 0.9:
            self.lower = not self.lower
        if self.lower:
            frame[model.lowerIndices] = [1,.5,.5]
        else:
            frame[model.upperIndices] = 1


def main(screen):

    # master parameters, used in rendering and updated by playlist advancer thread
    masterParams = EffectParameters()

    # if we got a curses screen, use it for button emulation through the keyboard
    if screen:
        # re-open stdout with a buffer size of 0. this makes print commands work again.
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        screen.clear()
        screen.refresh()

        # put keyboard state into effect parameters
        keymonitor = KeyboardMonitorThread(masterParams, screen)
        keymonitor.start()

    # model = SomaModel('../../cad/SomaPointParsing/input_points.json')
    model = SomaModel()

    # a playlist. each entry in a playlist can contain one or more effect layers
    # (if more than one, they are all rendered into the same frame...mixing method
    # is determined by individual effect layers' render implementations)
    playlist = Playlist([
        # [
        #    RandomPhaseLayer(model),
        #    ColorCycleLayer()
        # ],
        # [
        #    ColorPaletteBattleLayer(model)
        # ],
        [HolidayColorWiper(model,
            colors=[(204,31,31), (36,143,0), (255,255,255)],
            timer=3
        )
        ],
        # [
           #PhotoColorsLayer(model),
           # InvertColorsLayer(),
           #InvertColorByRegionLayer(model),
        # ],
        # [
        #     SineWaveLayer(color = (0.2, 0.5, 1)),
        #     # SomaTestLayer(),
        #     # ColorBlinkyLayer(),
        # ],
        # [
        #     PhotoColorsLayer(model),
        #     DimBrightButtonLayer(),

        #     # ColorWave(model),
        #     SpeckLayer(button=0),
        #     SpeckLayer(button=1),

        #     #PhotoColorsLayer(model),
        #     #DimBrightButtonLayer()
        #     #AddressTestLayer(),
        #     #TestPatternLayer(),
        #     #ColorWave(model),
        #     # ColorWiper(model),
        #      # MultiplierLayer(ColorWave(model), ColorWiper(model)),
        # ],
        # [
            # FireflySwarmLayer(),
            # ButtonTestLayer()
           # RandomPhaseLayer(model)
           # MultiplierLayer(AxonChaseLayer(),ColorWave(model))
           # AxonChaseLayer(segments=['all'])
           # ColorWave(model),
        #    ColorWave(model),
           # AxonChaseLayer()
        # ],
        # [
            # AxonChaseLayer(color=(0,1,0), trigger_threshold=0.2, cycle_time=1.5),
            # AxonChaseLayer(color=(0,0,1), trigger_threshold=0.1, cycle_time=1.5),
        # ],

    ])

    # the renderer manages a playlist (or dict of multiple playlists), as well as transitions
    # and gamma correction
    renderer = Renderer(playlists={'all': playlist}, gamma=2.2)

    # the controller manages the animation loop - creates frames, calls into the renderer
    # at appropriate intervals, updates the time stored in master params, and sends frames
    # out over OPC
    controller = AnimationController(model, renderer, masterParams)

    # a thread that periodically advances the active playlist within the renderer.
    # TODO: example to demonstrate swapping between multiple playlists with custom fades
    advancer = PlaylistAdvanceThread(renderer, switchInterval=10)
    advancer.start()

    # go!
    controller.drawingLoop()


if __name__ == '__main__':
    try:
        # try to import curses for keyboard button emulator
        import curses.wrapper
        curses.wrapper(main)
    except ImportError:
        # otherwise just run main with no curses screen
        main(None)
