# Pulse Light controller
# Python code for controlling the LEDs in the Pulse Pods

import datetime
import time
from operator import itemgetter, attrgetter
from select import select
import serial
import socket
import struct
import os
import sys
from pulse_model import *
from renderer import Renderer
from controller import AnimationController
from effectlayer import *
from pulse_effect_parameters import *
from effects.orbital import *
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
from effects.lightning import Lightning
from playlist import Playlist
from threading import Thread
from threads import PlaylistAdvanceThread, KeyboardMonitorThread
from random import random
from math import *
from network.commands import *

# Common variables
#BROADCAST_ADDR = "224.51.105.104"
#BROADCAST_ADDR = "255.255.255.255"
#BROADCAST_ADDR = "127.255.255.255"
BROADCAST_ADDR = "192.168.1.255"
HEARTBEAT_PORT = 5000
COMMAND_PORT   = 5001
MULTICAST_TTL  = 4
ALL_RECEIVERS  = 255

gReceiverId = 0 

class PulseListenerThread(Thread):
    allowHeartBeats = True
    currentHeartBeatSource = 0
    heartBeatListener = None
    commandListener   = None
    nextHeartBeatStartTime = 0
    lastHeartBeatStartTime = 0
    nextNextHeartBeatStartTime = 0
    running = False
   
    def __init__(self, controller, params):
        Thread.__init__(self)
        self.daemon = True
        self.controller = controller
        self.masterParams = params
        self.running = True
        
        self.heartBeatListener = self.createBroadcastListener(HEARTBEAT_PORT)
        self.commandListener   = self.createBroadcastListener(COMMAND_PORT)
        self.currentHeartBeatSource = gReceiverId
        

    def run(self):
        while True:
            self.processListeners()

    def processListeners(self):
        ''' Process events on the command socket and the heartbeat socket '''
        if not self.running:
            return
        try:
            readfds = [self.heartBeatListener, self.commandListener]
            if self.nextHeartBeatStartTime:
                waitTime = self.nextHeartBeatStartTime - datetime.datetime.now() 
                if waitTime < datetime.timedelta(seconds=0):
                    waitTime = datetime.timedelta(seconds=0)
                inputReady, outputReady, exceptReady = select(readfds, [], [], waitTime.total_seconds())
            else:
                inputReady, outputReady, exceptReady = select(readfds, [], []) 
            if inputReady:
                for fd in inputReady:
                    if fd is self.heartBeatListener:
                        heartBeatData = fd.recv(1024) 
                        self.handleHeartBeatData(heartBeatData)
                    elif fd is self.commandListener:
                        print "received command"
                        commandData = fd.recv(1024)
                        self.handleCommandData(commandData)
            # if we've gone past the nextHeartBeatStartTime, move up
            if self.nextHeartBeatStartTime:
               if self.nextHeartBeatStartTime -  datetime.datetime.now() <= datetime.timedelta(seconds=0):  
                    print "next heart beat expires!" 
                    
                    self.lastHeartBeatStartTime = self.nextHeartBeatStartTime
                    if self.nextNextHeartBeatStartTime:
                        print "next becomes current!" 
                        self.nextHeartBeatStartTime = self.nextNextHeartBeatStartTime
                        self.nextNextHeartBeatStartTime = None 
                    else:
                        if self.bps != 0: 
                            self.nextHeartBeatStartTime = self.nextHeartBeatStartTime + datetime.timedelta(seconds=1/self.bps)
               self.setMasterParams()
            
        except KeyboardInterrupt: 
            print "Keyboard interrupt detected, terminating"
            running = False
            self.terminate()
            
    def setMasterParams(self):
        # I believe this is thread-safe because of the python GIL
        self.masterParams.nextHeartBeatStartTime = self.nextHeartBeatStartTime
        self.masterParams.lastHeartBeatStartTime = self.lastHeartBeatStartTime
        self.masterParams.bps                    = self.bps

    def terminate(self):
        self.running = False
        self.heartBeatListener.close()
        self.commandListener.close()

    def createBroadcastListener(self, port, addr=BROADCAST_ADDR):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set some options to make it multicast-friendly
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass # Some systems don't support SO_REUSEPORT

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Bind to the port
        sock.bind(('', port))

        return sock
        
    def handleHeartBeatData(self, heartBeatData):    
        ### NB - XXX - This structure has to match the one in BPMPulseData_t BPMPulse.h
        # Called from the HeartBeatCommandThread
        pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)
        print "heartbeat pod_id is %d, looking for %d, bpm is %d" % (pod_id, self.currentHeartBeatSource, bpmApprox) 
        if pod_id is self.currentHeartBeatSource and self.allowHeartBeats:
            print "heartbeat we are interested in" 
            if beatOffsetMs < beatIntervalMs: # if we haven't already missed the 'next' beat...
                heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - beatOffsetMs)
            else:
                heartBeatStartTime = datetime.dateTime.now() + datetime.timedelta(milliseconds = beatIntervalMs - (beatOffsetMs % beatIntervalMs))
                
            # schedule next heart beat
            if self.nextHeartBeatStartTime:
                self.nextNextHeartBeatStartTime = heartBeatStartTime
            else:
                self.nextHeartBeatStartTime = heartBeatStartTime
                self.nextNextHeartBeatStartTime = None
 
            self.bps = bpmApprox/60
            print "Next heart beat time is ", self.nextHeartBeatStartTime
            print "Last heart beat time was ", self.lastHeartBeatStartTime
            print "Next next heart beat time is ", self.nextNextHeartBeatStartTime
 
    def handleCommandData(self, commandData):
        # Called from the HeartBeatCommandThread
        receiverId, commandTrackingId, command, data = struct.unpack("=BBHL", commandData)
        if ((receiverId is gReceiverId) or (receiverId is ALL_RECEIVERS)):
            if command is Commands.STOP_HEARTBEAT:
                self.allowHeartBeats = False
                self.stopHeartBeat()
            elif command is Commands.START_EFFECT:
                pass
            elif command is Commands.STOP_EFFECT:
                pass
            elif command is Commands.START_HEARTBEAT:
                self.allowHeartBeats = True
            #elif command is Commands.POD_R_TO_L_FLASH:
                # controller.renderer.addSpecialEffectLayer(WhateverTheFuckSpecialEffectLayerINeed)
            #    pass
            #elif command is Commands.POD_L_TO_R_FLASH:
                # XXX add special effect. See above non-code
            #    pass
            elif command is Commands.USE_HEARTBEAT_SOURCE:
                self.currentHeartBeatSource = data


class PodController(object):
    screen = None
    interval = 0
    masterParams = None

    def __init__(self, screen, interval):
        self.running = True
        self.screen = screen
        self.interval = interval

        # master parameters, used in rendering and updated by playlist advancer thread
        self.masterParams = PulseEffectParameters()

        # if we got a curses screen, use it for debug input through the keyboard
        if self.screen:
            # re-open stdout with a buffer size of 0. this makes print commands work again.
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
            self.screen.clear()
            self.screen.refresh()

            # put keyboard state into effect parameters
            keymonitor = KeyboardMonitorThread(self.masterParams, self.screen)
            keymonitor.start()

        points_filename = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             '..', 'models', 'pulse_pod.json'))
        model = PulseModel(points_filename=points_filename)

        # a playlist. each entry in a playlist can contain one or more effect layers
        # (if more than one, they are all rendered into the same frame...mixing method
        # is determined by individual effect layers' render implementations)
        playlist = Playlist([
            [
              AverageLayer(
                OrbitalLayer(0.0013, 0.0011, 3.0, 5.0, 1, 13.0),
                OrbitalLayer(0.0007, 0.0011, 8.0, 5.0, -1, 15.0),
              )
            ],
        ])

        # the renderer manages a playlist (or dict of multiple playlists), as well as transitions
        # and gamma correction
        renderer = Renderer(playlists={'all': playlist}, gamma=2.2)

        # the controller manages the animation loop - creates frames, calls into the renderer
        # at appropriate intervals, updates the time stored in master params, and sends frames
        # out over OPC
        controller = AnimationController(model, renderer, self.masterParams)

        # a thread that periodically advances the active playlist within the renderer.
        # TODO: example to demonstrate swapping between multiple playlists with custom fades
        advancer = PlaylistAdvanceThread(renderer, switchInterval=self.interval)
        advancer.start()
        
        # A thread that listens for heartbeats and special effects. Heartbeats information
        # will update the master parameters, which are available to all effect layers.
        # Special effects will be added as the last layer of effects
        pulseListenerThread = PulseListenerThread(self, self.masterParams)
        pulseListenerThread.start()

        
        try:
            controller.drawingLoop()
        except KeyboardInterrupt:
            pulseListenerThread.terminate()

        # go!
        # XXX - This is not going to get executed. If you want to do a nice pulsing heartbeat,
        # do it within an effect layer, rather than at this level. The parameters lastHeartBeat
        # try:
        #    while True:
        #        diminished = self.masterParams.beat * 0.8
        #        self.masterParams.beat = 0.0 if diminished < 0.0 else diminished
        #        print diminished
        #        controller.drawFrame()
        #except KeyboardInterrupt:
        #    pass

def main(args):
    #  - NB - this stuff is all going to get done by the startup script that calls this thing
    # sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    # # Redirect stderror to stdout
    # old = sys.stderr
    # sys.stderr = sys.stdout
    # old.close()

    print "Startup, PID", os.getpid()

    if len(args) > 1:
        print "Receiver Id is", int(args[1])
        gReceiverId = int(args[1])

    pod = PodController(None, 3)    

if __name__ == '__main__':
    main(sys.argv)
