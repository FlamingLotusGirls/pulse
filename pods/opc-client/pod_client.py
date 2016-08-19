# Pulse Light controller
# Python for controlling the heart fire effects. Will do heartbeat, other effects
# as directed.

# listen on broadcast receiver
# send out heartbeat poofs (and color poofs, and sparkle wtfs
# do special effects - chase, all poof, alterna-poof, throbbing poof

# XXX - TODO: Test serial connects, disconnects, reconnects... 
# XXX - TODO: Better cleanup
# XXX - TODO: Auto-start
# XXX - TODO: Schedule next heartbeat when previous one clears (allows us to miss heartbeats)
# XXX - TODO: Put common #defines in a shared piece of code

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
from threading import Thread
from threads import PlaylistAdvanceThread, KeyboardMonitorThread, ButtonMonitorThread
from random import random
from math import *

# Common variables
#BROADCAST_ADDR = "224.51.105.104"
#BROADCAST_ADDR = "255.255.255.255"
#BROADCAST_ADDR = "127.255.255.255"
BROADCAST_ADDR = "192.168.1.255"
HEARTBEAT_PORT = 5000
COMMAND_PORT   = 5001
MULTICAST_TTL  = 4
BAUDRATE       = 19200

# Effect ids (also common)
HEARTBEAT = 1
CHASE     = 2
ALLPOOF   = 3

# XXX could have fast heartbeats, and slow heartbeats, and big heartbeats,
# and little heartbeats. All types of heartbeats
# could I specify the timing of these things in the command channel? I could specify a timing multiplier

# Effect definitions
effects = {HEARTBEAT:[[1,1,0], [2,1,100], [1,0,200], [2,0,300]], 
           CHASE:    [[3,1,0], [4,1,100], [5,1,200], [3,0,300], [4,0,400], [5,0,500]],
           ALLPOOF:  [[3,1,0], [4,1,0],   [5,1, 0],  [3,0,700], [4,0,700], [5,0,700]]}

hexStr = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]         
def intToHex(myInt):
    if myInt < 0:
        return "0"
    modulus = myInt % 16
    div     = myInt // 16
    
    div = min(15, div)

    return hexStr[div] + hexStr[modulus]           

# Commands
class Commands():
    STOP_ALL             = 1
    STOP_HEARTBEAT       = 2
    START_HEARTBEAT      = 3
    START_EFFECT         = 4
    STOP_EFFECT          = 5
    USE_HEARTBEAT_SOURCE = 6


class HeartbeatCommandThread(Thread):
    def __init__(self, controller):
        Thread.__init__(self)
        self.daemon = True
        self.controller = controller

    def run(self):
        while True:
            self.controller.processListeners()
            time.sleep(1)


class PodController(object):
    screen = None
    interval = 0
    masterParams = None
    running = False
    allowHeartBeats = True
    currentHeartBeatSource = 0
    heartBeatListener = None
    commandListener = None
    eventQueue = None
    ser = None
    previousHeartBeatTime = None
    gReceiverId = 0  # XXX need to set the receiver Id, or more properly, the unit id, from a file or something

    gCurrentHeartBeat  = None
    gNextHeartBeat     = None
    gNextNextHeartBeat = None
    gNextHeartBeatStartTime     = 0
    gNextNextHeartBeatStartTime = 0

    gGlobalEffectId    = 0

    def __init__(self, screen, interval):
        self.running = True
        self.screen = screen
        self.interval = interval

        # master parameters, used in rendering and updated by playlist advancer thread
        self.masterParams = EffectParameters()

        # if we got a curses screen, use it for button emulation through the keyboard
        if self.screen:
            # re-open stdout with a buffer size of 0. this makes print commands work again.
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
            self.screen.clear()
            self.screen.refresh()

            # put keyboard state into effect parameters
            keymonitor = KeyboardMonitorThread(self.masterParams, self.screen)
            keymonitor.start()

        else:
            ButtonMonitorThread(self.masterParams).start()

        model = PulseModel(points_filename='./models/pulse_pod.json') #address_filename="../addresses.txt")

        # a playlist. each entry in a playlist can contain one or more effect layers
        # (if more than one, they are all rendered into the same frame...mixing method
        # is determined by individual effect layers' render implementations)
        playlist = Playlist([
            [
                RandomPhaseLayer(model),
                ColorCycleLayer(0.0053, 0.0),#0.0011
                # Lightning(),
                # Repair(),
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

        self.heartBeatListener = self.createBroadcastListener(HEARTBEAT_PORT)
        self.commandListener   = self.createBroadcastListener(COMMAND_PORT)
        self.ser = self.initSerial() #XXX need to handle serial disconnect, restart
        self.eventQueue = [] # NB - don't need a real queue here. Only one thread 
        
        HeartbeatCommandThread(self).start()

        # go!
        try:
            while True:
                diminished = self.masterParams.beat * 0.8
                self.masterParams.beat = 0.0 if diminished < 0.0 else diminished
                print diminished
                controller.drawFrame()
        except KeyboardInterrupt:
            pass

    def processListeners(self):
        if not self.running:
            return
        try:
            readfds = [self.heartBeatListener, self.commandListener]
            if not self.eventQueue:
                print "doing select, no timeout"
                inputReady, outputReady, exceptReady = select(readfds, [], []) 
            else:
                waitTime = (self.eventQueue[len(self.eventQueue)-1]["time"] - datetime.datetime.now()).total_seconds()
                print "!!doing select, timeout is %f" % waitTime
                waitTime = max(waitTime, 0)
                inputReady, outputReady, exceptReady = select(readfds, [], [], waitTime) 
            if inputReady:
                print "Have data to read"
                for fd in inputReady:
                    if fd is self.heartBeatListener:
                        print "received heartbeat"
                        heartBeatData = fd.recv(1024)
                        self.handleHeartBeatData(heartBeatData)
                    elif fd is self.commandListener:
                        print "received command"
                        commandData = fd.recv(1024)
                        self.handleCommandData(commandData)
            self.sendEvents()
        except KeyboardInterrupt: # need something besides a keyboard interrupt to stop? or not?XXX
            print "Keyboard interrupt detected, terminating"
            running = False
            self.terminate()

    def terminate(self):
        self.running = False
        self.heartBeatListener.close()
        self.commandListener.close()

    # XXX - since we're using a list, we probably want to be pulling off the end of the list
    # rather than the beginning. XXX TODO
    def createBroadcastListener(self, port, addr=BROADCAST_ADDR):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set some options to make it multicast-friendly
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass # Some systems don't support SO_REUSEPORT
    #    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    #    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


        # Bind to the port
        print "Addr is ", addr
        print port
    #    sock.bind((addr, port))
        sock.bind(('', port))

    #    # Set some more multicast options
    #    mreq = struct.pack("=4sl", socket.inet_aton(addr), socket.INADDR_ANY)
    #    sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        return sock
        
    # And we need to generate another heart beat if I dont hear one... XXX 
    def handleHeartBeatData(self, heartBeatData):    
      ### This structure has to match the one in BPMPulseData_t BPMPulse.h
        self.masterParams.beat = 1.0
        pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)
        print "heartbeat pod_id is %d bpm is %d" % (pod_id, bpmApprox) 
        if pod_id is self.currentHeartBeatSource and self.allowHeartBeats:
    #        stopHeartBeat() # XXX should allow the last bit of the heart beat to finish, if we're in the middle            
            
            if beatOffsetMs < beatIntervalMs: # if we haven't already missed the 'next' beat...
                heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - beatOffsetMs)
            else:
                heartBeatStartTime = datetime.dateTime.now() + datetime.timedelta(milliseconds = beatIntervalMs - (beatOffsetMs % beatIntervalMs))
                
            #if previousHeartBeatTime:
            #    heartBeatStartTime = previousHeartBeatTime + datetime.timedelta(milliseconds = beatIntervalMs)
            #else:
            #    heartBeatStartTime = datetime.datetime.now()
            
            # schedule next heart beat
            instanceId = self.loadEffect(HEARTBEAT, heartBeatStartTime, beatIntervalMs)
            
            # fix up additional heart beats already in the queue
            # if there's already a next heart beat, and the start time is *greater than* the incoming time, kill it
            self.helper_addHBReference(instanceId, heartBeatStartTime)
            
    #        if (gNextHeartBeat != None && gNextHeartBeatStartTime > heartBeatStartTime):
    #            # replace gNextHeartBeat
    #            removeEffectInstance(gNextHeartBeat)
    #            gNextHeartBeat = instanceId
    #            gNextHeartBeatStartTime = heartBeatStartTime
    #            # nuke NextNextHeartBeat
    #            removeEffectInstance(gNextNextHeartBeat)
    #            gNextNextHeartBeat = None
    #        else:
    #            # replaceNextNextHeartBeat
    #            if gNextNextHeartBeat != None:
    #                removeEffectInstance(gNextNextHeartBeat)
    #            gNextNextHeartBeat = instanceId
    #            gNextNextHeartBeatStartTime = heartBeatStartTime
                
            
          #  if heartBeatStartTime <= datetime.datetime.now():
          #      print "1"
          #      loadEffect(HEARTBEAT, datetime.datetime.now(), beatIntervalMs)
          #  else:
          #      print "2 ", heartBeatStartTime
          #      loadEffect(HEARTBEAT, heartBeatStartTime, beatIntervalMs)
                
            self.sortEventQueue()
                
    def helper_addHBReference(self, instanceId, heartBeatStartTime):
        print "adding reference for ", instanceId
        
        if (self.gNextHeartBeat == None or (self.gNextHeartBeat != None and self.gNextHeartBeatStartTime > heartBeatStartTime)):
            print "new heart beat replaces previous"
            # replace gNextHeartBeat
            self.removeEffectInstance(self.gNextHeartBeat)
            self.gNextHeartBeat = instanceId
            self.gNextHeartBeatStartTime = heartBeatStartTime
            # nuke NextNextHeartBeat
            self.removeEffectInstance(self.gNextNextHeartBeat)
            self.gNextNextHeartBeat = None
        else:
            # replaceNextNextHeartBeat
            if self.gNextNextHeartBeat != None:
                self.removeEffectInstance(self.gNextNextHeartBeat)
            self.gNextNextHeartBeat = instanceId
            self.gNextNextHeartBeatStartTime = heartBeatStartTime
            
        print "Next hbId is ", self.gNextHeartBeat
        print "NextNext hbId is ", self.gNextNextHeartBeat

            
    def sortEventQueue(self):
        self.eventQueue.sort(key=itemgetter("time"), reverse=True)

    def handleCommandData(self, commandData):
        receiverId, commandTrackingId, commandId = struct.unpack("=BBH", commandData)
        if receiverId is gReceiverId:                  # it's for us!
            if command is Command.STOP_ALL:
                self.removeAllEffects()
            elif command is STOP_HEARTBEAT:
                self.allowHeartBeats = False
                self.stopHeartBeat()
            elif command is START_EFFECT:
                dummy1, dummy2, dummy3, effectId = struct.unpack("=BBHL", commandData)
                self.loadEffect(effectId, datetime.datetime.now())
            elif command is STOP_EFFECT:
                dummy1, dummy2, dummy3, effectId = struct.unpack("=BBHL", commandData)
                self.removeEffect(effectId)
            elif command is START_HEARTBEAT:
                self.allowHeartBeats = True
            elif command is USE_HEARTBEAT_SOURCE:
                dummy1, dummy2, dummy3, pod_id = struct.unpack("=BBHL", commandData)
                self.currentHeartBeatSource = pod_id
        
            self.sortEventQueue()
            
        # could have a define effect as well... XXX MAYBE
        
    def removeEffect(self, effectId):
        print "removing effect ", effectId
        for event in self.eventQueue:
            if event["effectId"] is effectId:
                self.eventQueue.remove(event) 
                
    def removeEffectInstance(self, instanceId):
        print "removing instance", instanceId
        if instanceId == None:
            return
            
        for event in self.eventQueue:
            print "  found event", event
            if event["globalId"] == instanceId:
                print "   removing an event", event
                self.eventQueue.remove(event) 


    # canonical event is the effectId, the globalEffectId, the controllerId, the channel, on/off, the timestamp,
    # and the interval at which to repeat the effect.
    # Note that the effectId is which *type* of effect. The globalEffectId is a unique id for an effect instance
    def loadEffect(self, effectId, starttime, repeatMs=0):
        # NB - repeating events are special, because they automatically schedule themselves.
        # Only one of a particular type is allowed to be in the queue at a time, so if
        # there is already one, delete it.
        if repeatMs != 0 and effectId != HEARTBEAT:
            removeEffect(effectId)
            
        # Now set up the event queue with the events in this effect
        if effects[effectId] != None:
            globalId = self.gGlobalEffectId
            nEvents = len(effects[effectId])
            eventIdx = 0
            for event in effects[effectId]:
                canonicalEvent = {}
                canonicalEvent["effectId"]     = effectId
                print "add event" + str(event)
                canonicalEvent["globalId"]     = globalId
                canonicalEvent["controllerId"] = intToHex(event[0]//8)
                canonicalEvent["channel"]      = event[0] %8
                canonicalEvent["onOff"]        = event[1]
                canonicalEvent["time"]         = starttime + datetime.timedelta(milliseconds = event[2])
                if eventIdx + 1 >= nEvents and repeatMs != 0:  
                    canonicalEvent["nextStartTime"] = starttime + datetime.timedelta(milliseconds = repeatMs)
                    canonicalEvent["repeatMs"]      = repeatMs
                else:
                    canonicalEvent["repeatMs"] = 0
                #print "canonical event is " + str(canonicalEvent)
                #print "timedelta is " + str(datetime.timedelta(milliseconds = event[2]))
                
                self.eventQueue.append(canonicalEvent)
                eventIdx += 1
            self.gGlobalEffectId += 1
            
        return globalId
            
    def removeAllEffects(self):
        self.eventQueue = []
        
    def stopHeartBeat(self):
        self.removeEffect(HEARTBEAT)
        
    def initSerial(self):
        ser = serial.Serial()
        ser.baudrate = BAUDRATE
        port = False
        for filename in os.listdir("/dev"):
            if filename.startswith("tty.usbserial"):  # this is the ftdi usb cable on the Mac
                port = "/dev/" + filename
                print "Found usb serial at ", port
                break;
            elif filename.startswith("ttyUSB0"):      # this is the ftdi usb cable on the Pi (Linux Debian)
                port = "/dev/" + filename
                print "Found usb serial at ", port
                break;
        
        if not port:
            print("No usb serial connected")
            return None

        ser.port = port
        ser.timeout =0 
        ser.stopbits = serial.STOPBITS_ONE
        ser.bytesize = 8
        ser.parity   = serial.PARITY_NONE
        ser.rtscts   = 0 
        ser.open() # if serial open fails... XXX
        return ser

    def createEventString(self, events):
        if not events:
            return None
        
        # for each controller, create event string
        # send event string
        eventString = ""
        controllerId = -1
        firstEvent = True
        for event in events:
            # print "Event is " + str(event)
            if event["controllerId"] != controllerId:
                controllerId = event["controllerId"]
                if not firstEvent:
                    eventString = eventString + "."
                eventString = eventString + "!%s" % controllerId
            else:
                eventString = eventString + "~"
            
            eventString = eventString + "%i%s" % (event["channel"], event["onOff"])
            
        eventString = eventString + "."
        
        return eventString    
                            
                     
    def sendEvents(self):
        if (len(self.eventQueue) == 0):
            return
        
        # getting all the events we want to get
        currentEvents = []
        currentTime = datetime.datetime.now()
        timewindow = currentTime + datetime.timedelta(milliseconds = 5)
        #print "timewindow is ", timewindow
        #print "currentTime is ", currentTime
        event = self.eventQueue.pop()
        while event and event["time"] < timewindow:
            #print "Adding event with time ", event["time"]
            currentEvents.append(event)
            try:
                event = self.eventQueue.pop()
            except IndexError:
                break
        if event["time"] >= timewindow: 
            self.eventQueue.append(event)  # XXX is this going to go on the correct side of the queue?
        if currentEvents:
            currentEvents.sort(key=itemgetter("controllerId"))
            eventString = self.createEventString(currentEvents)
            print "Event string is %s" %eventString
            if not self.ser:
                self.ser = self.initSerial()
            if self.ser:
                try:
                    ser.write(eventString.encode())   # XXX what are all the ways this might fail?
                except IoException:
                    ser.close()
                    ser = None
            for event in currentEvents:
                # if we're starting a heartbeat, reset the pointers to current, next, and next next heartbeat ids
                print "playing effect instance ", event["globalId"]
                print "nextHeartBeat is ", self.gNextHeartBeat
                if event["globalId"] == self.gNextHeartBeat:
                    self.gCurrentHeartBeat = event["globalId"]
                    self.gNextHeartBeat = self.gNextNextHeartBeat
                    self.gNextHeartBeatStartTime = self.gNextNextHeartBeatStartTime
                    self.gNextNextHeartBeat = None
                    print "Starting heart beat ", self.gCurrentHeartBeat
                    print "Next beat is ", self.gNextHeartBeat
                # if we're ending a heartbeat, load up the next one and reset pointers...
                if event["repeatMs"] != 0:
                    instanceId = None
                    if (event["effectId"] == HEARTBEAT):
                        self.gCurrentHeartBeat = None
                        if (self.gNextHeartBeat == None):
                            instanceId = self.loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"]) 
                            self.helper_addHBReference(instanceId, event["nextStartTime"])
                    else:
                        instanceId = loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"]) # XXX what thread is this normally called from?

                    if instanceId != None:
                        print "Auto schedule instance ", instanceId
                        self.sortEventQueue()

if __name__ == '__main__':
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    # Redirect stderror to stdout
    old = sys.stderr
    sys.stderr = sys.stdout
    old.close()

    print "Starup, PID", os.getpid()

    pod = PodController(None, 3)
