#!/usr/bin/env python
from pulse_model import *
from renderer import Renderer
from controller import AnimationController
from effectlayer import *
from effects.color_cycle import *
from effects.random_phase import *
from effects.random_blink_cycle import *
from effects.chase import AxonChaseLayer
from effects.colorwave import ColorWave
from effects.colorwiper import ColorWiper
from effects.invert import InvertColorsLayer, InvertColorByRegionLayer
from effects.color_palette_battle import *
from effects.photo_colors import *
from effects.clamp import *
from effects.dim_bright_button_layer import *
from effects.button_flash import ButtonFlash
from effects.specklayer import SpeckLayer
from effects.lower import LowerLayer
from effects.upper import UpperLayer
from effects.axon import AxonLayer
from effects.morse2 import MorseLayer2
from effects.lightning import Lightning
from effects.repair import Repair
from playlist import Playlist
from threads import PlaylistAdvanceThread, KeyboardMonitorThread, ButtonMonitorThread
from random import random
from math import *
import os
import sys

def main(screen, interval):

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

    else:
        ButtonMonitorThread(masterParams).start()

    model = PulseModel(points_filename='./models/pulse_pod.json') #address_filename="../addresses.txt")

    # a playlist. each entry in a playlist can contain one or more effect layers
    # (if more than one, they are all rendered into the same frame...mixing method
    # is determined by individual effect layers' render implementations)
    playlist = Playlist([

        # This is a very handy layer for debugging.  Steps through LEDs in
        # order of frame index in response to a button push, printing the
        # address of the lit LED.
        # [ControlledAddressTestLayer()],

        #[TriangleWaveLayer()],

        # [
        #     PhotoColorsLayer(model),
        #     DimBrightButtonLayer(),
        #     SpeckLayer(button=0),
        #     SpeckLayer(button=1),
        #     Repair(),
        # ],

        # [
        #     MultiplierLayer(ColorWave(model, grayscale=True), ColorWiper(model)),
        #     # Repair(),
        # ],

        [
            RandomPhaseLayer(model),
            ColorCycleLayer(0.00003, 0.0011),
            # Lightning(),
            # Repair(),
        ],

        # [
        #    ColorPaletteBattleLayer(model),
        #    # Repair(),
        # ],

        # [
        #     MorseLayer2(["figure", "action", "light", "yang", "synergy", "unity in dual", "SOMA"], ["ground", "intention", "darkness", "yin", "discord", "order from chaos", "FLG"]),
        #     ColorCycleLayer(0.0003, 0.0005),
        #     Lightning(),
        #     # Repair(),
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

    advancer = PlaylistAdvanceThread(renderer, switchInterval=interval)
    advancer.start()

    # go!
    controller.drawingLoop()

if __name__ == '__main__':
    #try:
    #    # try to import curses for keyboard button emulator
    #    import curses.wrapper
    #    curses.wrapper(main)
    #except ImportError:
    #    # otherwise just run main with no curses screen
    #    main(None)

    # Unbuffer stdout (simulating python's "-u" flag)
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    # Redirect stderror to stdout
    old = sys.stderr
    sys.stderr = sys.stdout
    old.close()

    print "Starup, PID", os.getpid()

    interval = 3
    main(None, interval)
