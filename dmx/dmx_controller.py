# Python for controlling the DMX lights according to UDP packets
# Some (most) code was shamelessly stolen from Carolyn Wales

# TODO: Shut off heartbeats when packets aren't being sent in anymore. This is related to using BPM to time heartbeats sine currently excess heartbeats are being put into the queue

import datetime
import os
from operator import itemgetter, attrgetter
import math
from select import select
import serial
import socket
import struct
import sys
import pysimpledmx
import threading
import time
import random

from network.commands import *

BROADCAST_ADDR = "192.168.1.255"
HEARTBEAT_PORT = 5000
COMMAND_PORT   = 5001
MULTICAST_TTL  = 4
BAUDRATE       = 19200

# NB - we make the assumption that the address starts at 2.
# Additional independent lights will have addresses at 
# 2 + n*6
DMX_RED_CHANNEL   = 2 # We start on 2 rather than 1 because pysimpledmx doesnt like 1
DMX_GREEN_CHANNEL = 3
DMX_BLUE_CHANNEL  = 4
DMX_WHITE_CHANNEL = 5
DMX_AMBER_CHANNEL = 6
DMX_UV_CHANNEL    = 7

# DMX channel count determines how many DMX channels are used by each light.
# 6 allows you control of just the LEDs (R,G,B,W,A,UV)
# 7 allows you control of the LEDs plus a master dimmer
# 8 allows you control of the LEDs and the dimmer, plus a strobe effect
# 12 allows you control of the LEDs, dimmer, and strobe, plus pre-programmed chases and standard LED combinations
DMX_CHANNEL_COUNT = 6 # Can be 6/7/8/12

# allow for 4 independently controlled lights - which is what we have!
ALL_RED_CHANNELS = [DMX_RED_CHANNEL, DMX_RED_CHANNEL + DMX_CHANNEL_COUNT,\
                    DMX_RED_CHANNEL + 2 * DMX_CHANNEL_COUNT, \
                    DMX_RED_CHANNEL + 3 * DMX_CHANNEL_COUNT]

ALL_GREEN_CHANNELS = map(lambda x: x+(DMX_GREEN_CHANNEL-DMX_RED_CHANNEL), ALL_RED_CHANNELS)
ALL_BLUE_CHANNELS = map(lambda x: x+(DMX_BLUE_CHANNEL-DMX_RED_CHANNEL), ALL_RED_CHANNELS)
ALL_WHITE_CHANNELS = map(lambda x: x+(DMX_WHITE_CHANNEL-DMX_RED_CHANNEL), ALL_RED_CHANNELS)
ALL_COLOR_CHANNELS = ALL_RED_CHANNELS + ALL_GREEN_CHANNELS + ALL_BLUE_CHANNELS

# channel offset from dmx device id. For some completely unknown reason, pysimpledmx
# starts the counting at channel 2 rather than channel 1.
RED_OFFSET    = 1
GREEN_OFFSET  = 2
BLUE_OFFSET   = 3
WHITE_OFFSET  = 4
AMBER_OFFSET  = 5
UV_OFFSET     = 6
DIMMER_OFFSET = 7
STROBE_OFFSET = 8


allowHeartBeats = True
allowSingleColor = True
allowStrobing = True
isStrobing = False
dmx = None
eventQueue = None
gEventQueueLock = threading.Lock()
gHeartBeatsPaused = False

gReceiverId = 3

# Named effects...
HEARTBEAT = 1
STROBE    = 2
SINGLE    = 3
FADEUP_RED = 4

FRAMES_PER_SECOND = 20

# effect element types
SET  = 1
FADE = 2
STROBE_FX = 3 

WAIT_HB_SECONDS = 5

gCurrentHeartBeatSource = 0 
gCurrentHeartBeat  = None
gNextHeartBeat     = None
gNextNextHeartBeat = None
gNextHeartBeatStartTime     = 0
gNextNextHeartBeatStartTime = 0
gUseSyntheticAsBackup = False
gLastHbReceiveTime = datetime.datetime.now()
gGlobalBeatOffsetMs = 0

gGlobalEffectInstance = 0

# Effects format ---  EFFECT:[[channels], intensity, duration from start of heartbeat(ms)]
# NB - channel is not currently being used in the heartbeat. It just does all red channels.
#effects = {HEARTBEAT:[[1,100,0], [2,250,50], [1,100,125], [2,180,200], [1,100,250]],
#effects = {HEARTBEAT:[[1,100,0], [1,250,125], [1,100,200], [1,180,275], [1,100,325]],
#effects = {HEARTBEAT:[[1,250,0], [1,100,100], [1,180,225], [1,100,275]],
#            STROBE:    [[3,1,0], [4,1,100], [5,1,200], [3,0,300], [4,0,400], [5,0,500]]}

effects = {HEARTBEAT:[[SET,[1],[255,255,0],0], [SET,[1],[100,100,0],100], [SET,[1],[180,180,0],225], [SET,[1],[100,100,0],275]],
#            STROBE:    [[SET,3,1,0], [SET,4,1,100], [SET,5,1,200], [SET,3,0,300], [SET,4,0,400], [SET,5,0,500]],
            STROBE:    [[STROBE_FX,[1], 0]],
            FADEUP_RED: [[FADE, [1], [0,0,0], [255,0,0], 0, 2000]]}
# nb - should be nice to have a sense of the current color, and then fade from current to 
# new. Current color could be specified by [], the empty array


# {HEARTBEAT:[[1,100,100], [2,250,200], [1,80,300], [2,180,400], [1,100,500]],

# {HEARTBEAT:[[1,100,100], [2,250,150], [1,80,275], [2,180,400], [1,100,450]],

# {HEARTBEAT:[[1,100,100], [2,250,150], [1,100,225], [2,180,300], [1,100,350]],


def createBroadcastListener(port, addr=BROADCAST_ADDR):
    ''' Create UDP listener at appropriate broadcast port/address '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Set some options to make it multicast-friendly
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass # Some systems don't support SO_REUSEPORT

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


    # Bind to the port
    print "Addr is ", addr
    sock.bind(('', port))

    return sock


def handleHeartBeatData(heartBeatData):
    ''' Handle heartbeat pulse from the UDP heartbeat socket. We act on the heartbeat
    pulse if it's from the source that we are listening to, or if we haven't received
    a heartbeat from our preferred source within several seconds, if the heartbeat
    is from the global synthetic heartbeat source (id 0).
    
    Note also that we do not act on heartbeats with bpm or beatInterval == 0, as these
    are generated as keep alives by the physical heartbeat detector when no heartbeat
    is actually detected.'''
    
    global gUseSyntheticAsBackup
    global gLastHbReceiveTime
    global gGlobalBeatOffsetMs
    
    global allowHeartBeats
    if not allowHeartBeats or gHeartBeatsPaused:
        print "received heartbeats, but none allowed right now" 
        return
    
    timeNow = datetime.datetime.now()

    if (timeNow - gLastHbReceiveTime > datetime.timedelta(seconds = WAIT_HB_SECONDS)):
        if not gUseSyntheticAsBackup:
            print "Swap to synthetic source"
            gUseSyntheticAsBackup = True
        
    pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)

    if ((bpmApprox != 0 and beatIntervalMs > 0) and ((pod_id is gCurrentHeartBeatSource and allowHeartBeats) or
       (gUseSyntheticAsBackup and pod_id is 0))):
        if pod_id is gCurrentHeartBeatSource and pod_id != 0:
            gUseSyntheticAsBackup = False
            gLastHbReceiveTime = timeNow
       
        if beatOffsetMs - gGlobalBeatOffsetMs < beatIntervalMs: # if we haven't already missed the 'next' beat...
            heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - (beatOffsetMs - gGlobalBeatOffsetMs))
        else:
            heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - ((beatOffsetMs - gGlobalBeatOffsetMs) % beatIntervalMs))

        instanceId = loadEffect(HEARTBEAT, heartBeatStartTime, beatIntervalMs)

        processNextHeartBeat(instanceId, heartBeatStartTime)

        sortEventQueue()


def processNextHeartBeat(instanceId, heartBeatStartTime):
    ''' Helper function - now that we have received a valid heartbeat, 
    fix up internal structures so that we will play the heartbeat at the appropriate 
    time '''
    
    global gNextHeartBeat
    global gNextNextHeartBeat
    global gNextHeartBeatStartTime
    global gNextNextHeartBeatStartTime

    if (gNextHeartBeat == None or (gNextHeartBeat != None and gNextHeartBeatStartTime > heartBeatStartTime)):
        removeEffectInstance(gNextHeartBeat)
        gNextHeartBeat = instanceId
        gNextHeartBeatStartTime = heartBeatStartTime

        removeEffectInstance(gNextNextHeartBeat)
        gNextNextHeartBeat = None

    else:
        if gNextNextHeartBeat:
            removeEffectInstance(gNextNextHeartBeat)
        gNextNextHeartBeat = instanceId
        gNextNextHeartBeatStartTime = heartBeatStartTime

    #print "Setting all white channels OFF"
    #dmx.setChannel(ALL_WHITE_CHANNELS, 0)

def pauseHeartBeats():
    global gHeartBeatsPaused
    gHeartBeatsPaused = True

def resumeHeartBeats():
    global gHeartBeatsPaused
    global gNextHeartBeat
    global gNextNextHeartBeat

    gHeartBeatsPaused = False
    gNextHeartBeat = None
    gNextNextHeartBeat = None

def handleCommandData(commandData):
    ''' Handle command data from the UDP command socket. Commands may turn on or off
    heartbeat response, set up special effects '''
    
    global gCurrentHeartBeatSource
    global allowHeartBeats
    global allowSingleColor
    global isStrobing

    receiverId, commandTrackingId, commandId, commandData = struct.unpack("=BBHl", commandData)
    if receiverId is gReceiverId:                  # it's for us!
        if commandId is Commands.STOP_ALL:
            allowHeartBeats = False
            allowSingleColor = False
            isStrobing = False
            removeAllEffects()
        elif commandId is Commands.STOP_HEARTBEAT:
            stopHeartBeat()
        elif commandId is Commands.START_HEARTBEAT:
            allowHeartBeats = True
        elif commandId is Commands.DMX_SINGLE_COLOR:
            dmxSingleColor(commandData)
        elif commandId is Commands.DMX_STROBE:
            print "Received Strobe command" 
            dmxStrobe(commandData)
        elif commandId is 20:
            dmxFade(commandData)
        elif commandId is Commands.USE_HEARTBEAT_SOURCE:
            gCurrentHeartBeatSource = commandData
            print "Received new heartbeat source, is ", gCurrentHeartBeatSource
        sortEventQueue() #Necessary?

def dmxStrobe(commandData):
    ''' Handle strobe command. Command data contains length of time to strobe. '0' means
    strobe until another effect command (start heartbeat, fade, single color) comes in. '''
    global isStrobing
    global gHeartBeatsPaused

    if isStrobing:
        removeEffect(STROBE)
        print "Setting all color channels OFF, autorender"
        dmx.setChannel(ALL_RED_CHANNELS + ALL_GREEN_CHANNELS +
                    ALL_BLUE_CHANNELS, 0, autorender=True)
        isStrobing = False
        return

    # Not strobing, so add strobe to eventQueue
    removeEffect(HEARTBEAT)
    pauseHeartBeats()
    print "Strobe start: Setting all white channels ON"
    dmx.setChannel(ALL_WHITE_CHANNELS, 0)
    loadEffect(STROBE, datetime.datetime.now(), 300, datetime.datetime.now() + datetime.timedelta(milliseconds=commandData))
    
def dmxFade(commandData):
    removeAllEffects()
    pauseHeartBeats()
    loadEffect(FADEUP_RED, datetime.datetime.now())

def dmxSingleColor(commandData):
    ''' Set the display to a single RGB color
    The command data is a long, with the first 8 bits used as a device mask, and
    the last 24 bits the RGB data '''
    global allowSingleColor
#    allowSingleColor =  not allowSingleColor

    if allowSingleColor:
        removeEffect(HEARTBEAT)
        removeEffect(STROBE)
        allowHeartBeats = False
        isStrobing = False
        #print "Single color - Setting all white channels ON, autorender"
        channelArray = []
        channelMask = (commandData & 0xff000000) >> 24
        for i in range(8):
            if channelMask & (1 << i):
                channelArray.append(i+1)
        
        if (commandData & 0x00ffffff != 0x00ffffff):
            dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + RED_OFFSET,   channelArray), (commandData & 0x00ff0000) >> 16)
            dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + GREEN_OFFSET, channelArray), (commandData & 0x0000ff00) >> 8)
            dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + BLUE_OFFSET,  channelArray), (commandData & 0x000000ff))
            dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + WHITE_OFFSET, channelArray), 0)
        else: 
            dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + WHITE_OFFSET, channelArray), 255)
            
        dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + AMBER_OFFSET, channelArray), 0)
        dmx.render()
#    else:
#        print "Setting all white channels OFF, autorender"
#        dmx.setChannel(ALL_WHITE_CHANNELS, 0, autorender=True)

def stopHeartBeat():
    global allowHeartBeats
    global eventQueue
    with gEventQueueLock:
        eventQueue[:] = [e for e in eventQueue if (e.get("effectId") != HEARBTEAT)]
    allowHeartBeats = False

def removeEffect(effectId):
    global eventQueue
    with gEventQueueLock:
        eventQueue[:] = [e for e in eventQueue if (e.get("effectId") == effectId)]

def removeEffectInstance(instanceId):
    global eventQueue
    if not instanceId:
        return

    with gEventQueueLock:
        eventQueue[:] = [e for e in eventQueue if (e.get("globalInstance") != instanceId)]


def removeAllEffects():
    global eventQueue
    with gEventQueueLock:
        eventQueue = []
    isStrobing = False
    
def eventSectionGetTime(eventSection, startTime):
    
    eventTime = 0
    # switch on event section type
    if eventSection[0] == SET:
        eventTime = eventSection[3]
    elif eventSection[0] == FADE:
        eventTime = eventSection[4]
    elif eventSection[0] == STROBE:
        eventTime = eventSection[2]
    else:
        pass
        
    return startTime + datetime.timedelta(milliseconds = eventTime)
    
def eventSectionGetStartColor(eventSection):
    ''' return the start color of the event, as a triple with range 0...255 '''
    if eventSection[0] == SET or eventSection[0] == FADE:
        if len(eventSection) >= 3 and len(eventSection[2]) >= 3:
            return eventSection[2][0], eventSection[2][1], eventSection[2][2]
        else:
            return 0,0,0
    else:
        return 0,0,0

def eventSectionGetEndColor(eventSection):
    ''' return the end color of the event, as a triple with range 0...255. 
    If the section has no end color, will return the start color '''
    if eventSection[0] == FADE:
        if len(eventSection) >= 4 and len(eventSection[3]) >= 3:
            return eventSection[3][0], eventSection[3][1], eventSection[3][2]
        else:
            return 0,0,0
    elif eventSection[0] == SET:
        if len(eventSection) >= 3 and len(eventSection[2]) >= 3:
            return eventSection[2][0], eventSection[2][1], eventSection[2][2]
        else:
            return 0,0,0
    else:
        return 0,0,0

def loadEffect(effectId, startTime, repeatMs=0, stopTime = None): # TODO: The information we need is heartbeat duration
    ''' Queue up an effect. There can be only a single one-shot effect in the 
        queue at a time, but there can be multiple repeating effects (Although in practice,
        the only repeating effect is the heartbeat) '''
    global gGlobalEffectInstance
   
    if repeatMs != 0 and effectId != HEARTBEAT:
        removeEffect(effectId)

    effectInstance = gGlobalEffectInstance

    index = 0
    nEvents = len(effects[effectId])
    for eventSection in effects[effectId]:
        event = {}
        if eventSection[0] == SET or eventSection[0] == STROBE_FX:
            red, green, blue = eventSectionGetStartColor(eventSection)
            event["effectId"]       = effectId
            event["globalInstance"] = effectInstance
            event["time"] = eventSectionGetTime(eventSection, startTime)
            event["color"] = [red, green, blue]
            event["devices"] = eventSection[1]
            event["stopTime"] = stopTime
            event["type"] = eventSection[0]
            event["effectEnd"] = False
            event["repeatMs"] = 0

            if index >= nEvents-1: 
                if repeatMs != 0:
                    event["repeatMs"] = repeatMs
                    event["nextStartTime"] = startTime + datetime.timedelta(milliseconds = repeatMs)
                else:
                    event["effectEnd"] = True                
            with gEventQueueLock:
                eventQueue.append(event)
        elif eventSection[0] == FADE: # creating individual simple events for the fade
            eventStartTime      = eventSectionGetTime(eventSection, startTime)
            eventEndTime        = eventStartTime + datetime.timedelta(milliseconds = eventSection[5])
            nFrames = int((eventEndTime - eventStartTime).total_seconds()*FRAMES_PER_SECOND)
            # we're going to use a logarithmic fade, because someone on the interwebs says it's more pleasing
            startR, startG, startB = eventSectionGetStartColor(eventSection)
            endR, endG, endB       = eventSectionGetEndColor(eventSection)
            startR = math.log(max(1,startR))
            endR   = math.log(max(1,endR))
            rangeR = endR - startR
            deltaR = rangeR/nFrames
            logRed = startR
            
            startG = math.log(max(1,startG))
            endG   = math.log(max(1,endG))
            rangeG = endG - startG
            deltaG = rangeG/nFrames
            logGreen = startG
            
            startB = math.log(max(1,startB))
            endB   = math.log(max(1,endB))
            rangeB = endB - startB
            deltaB = rangeB/nFrames
            logBlue = startB
            
            for i in range(nFrames+1):
                event = {}
                red   = int(math.exp(logRed))
                green = int(math.exp(logGreen))
                blue  = int(math.exp(logBlue))
                event["effectId"]       = effectId
                event["globalInstance"] = effectInstance
                event["time"]  = eventStartTime + datetime.timedelta(seconds = (1.0/FRAMES_PER_SECOND) * i)
                event["color"] = [max(min(red,255),0), max(min(green,255),0), max(min(blue,255),0)]
                event["devices"] = eventSection[1]
                event["type"] = eventSection[0]
                event["effectEnd"] = False
                event["repeatMs"] = 0
                if index >= nEvents-1 and i >= nFrames: 
                    if repeatMs != 0:
                        event["repeatMs"] = repeatMs
                        event["nextStartTime"] = startTime + datetime.timedelta(milliseconds = repeatMs)
                    else:
                        print "Setting effect end flag to True" 
                        event["effectEnd"] = True
                with gEventQueueLock:
                    eventQueue.append(event)
                logRed   += deltaR
                logBlue  += deltaB
                logGreen += deltaG
            
        index += 1

    gGlobalEffectInstance += 1
    return effectInstance

def loadEffect_old(effectId, startTime, repeatMs=0): # TODO: The information we need is heartbeat duration
    ''' Queue up an effect. There can be only a single one-shot effect in the 
        queue at a time, but there can be multiple repeating effects (Although in practice,
        the only repeating effect is the heartbeat) '''
    global gGlobalEffectInstance
    
    if repeatMs != 0 and effectId != HEARTBEAT:
        removeEffect(effectId)

    effectInstance = gGlobalEffectInstance

    if effectId is HEARTBEAT:
        index = 0
        nEvents = len(effects[effectId])
        for eventSection in effects[effectId]:
            event = {}
            event["effectId"] = effectId
            event["globalInstance"] = gGlobalEffectInstance
            event["sectionIndex"] = index
            index += 1

            if repeatMs != 0:
                if eventSection[2] == 0: #If duration is zero, run until end
                    event["time"] = startTime + datetime.timedelta(milliseconds = repeatMs)
                else:
                    event["time"] = startTime + datetime.timedelta(milliseconds = eventSection[2])
                if index >= nEvents:
                    event["repeatMs"] = repeatMs
                    event["nextStartTime"] = startTime + datetime.timedelta(milliseconds = repeatMs)
                else:
                    event["repeatMs"] = 0
            else:
                # TODO: Still need to figure out times for each event
                event["time"] = startTime + datetime.timedelta(milliseconds = 1000)
            with gEventQueueLock:
                eventQueue.append(event)
    elif effectId is STROBE:
        event = {}
        event["effectId"] = effectId
        event["time"]     = startTime
        event["repeatMs"] = repeatMs
        event["globalInstance"] = gGlobalEffectInstance
        with gEventQueueLock:
            eventQueue.append(event)

    gGlobalEffectInstance += 1

    return effectInstance


def sortEventQueue():
    with gEventQueueLock:
        eventQueue.sort(key=itemgetter("time"), reverse=True)


def renderEvents():
    ''' Go through the event queue, looking for events that we need to instantiate, which
    is to say, all events that are either scheduled in the past, or within 5 ms of the 
    current time. Repeating events will automatically reschedule themselves '''
    if len(eventQueue) == 0:
        return
    global dmx

    global gCurrentHeartBeat
    global gNextHeartBeat
    global gNextHeartBeatStartTime
    global gNextNextHeartBeat
    global gNextNextHeartBeatStartTime

    currentEvents = []
    currentTime = datetime.datetime.now()
    timeWindow = currentTime + datetime.timedelta(milliseconds = 5)
    
    with gEventQueueLock:
        event = eventQueue.pop()

        while event and event["time"] < timeWindow:
            currentEvents.append(event)
            try:
                event = eventQueue.pop()
            except IndexError:
                break
        if event["time"] >= timeWindow:
            eventQueue.append(event)
            #sortEventQueue()

    if currentEvents:
        if not dmx:
            dmx = initDMX()
            if not dmx:
                return
                
        for event in currentEvents:
            if event["type"] == STROBE_FX: # strobe is seriously weird
                processStrobe(event)
            else:
                dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + RED_OFFSET,   event["devices"]), event["color"][0])
                dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + GREEN_OFFSET, event["devices"]), event["color"][1])
                dmx.setChannel(map(lambda x: (x-1)*DMX_CHANNEL_COUNT + 1 + BLUE_OFFSET,  event["devices"]), event["color"][2])
                
                if event["globalInstance"] == gNextHeartBeat:
                    gCurrentHeartBeat = event["globalInstance"]
                    gNextHeartBeat = gNextNextHeartBeat
                    gNextHeartBeatStartTime = gNextNextHeartBeatStartTime
                    gNextNextHeartBeat = None
                if event["repeatMs"] != 0:
                    instanceId = None
                    if (event["effectId"] == HEARTBEAT):
                        gCurrentHeartBeat = None
                        if (gNextHeartBeat == None):
                            instanceId = loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"])
                            processNextHeartBeat(instanceId, event["nextStartTime"])
                    else:
                        instanceId = loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"])

                    if instanceId != None:
                        #print "Auto schedule instance ", instanceId
                        sortEventQueue()
                elif event["effectEnd"] == True:
                    print ("Ending effect, allowing heartbeats") 
                    resumeHeartBeats()
                    
        dmx.render()
        
        
def processHeartbeat(event):
    global dmx
    if not allowHeartBeats or gHeartBeatsPaused:
        return

    heartbeatSection = effects[HEARTBEAT][event["sectionIndex"]]

    print "(Autorender) Setting all red channels to ", heartbeatSection[1]
    dmx.setChannel(ALL_RED_CHANNELS, heartbeatSection[1], autorender=True)

def processStrobe(event):
    ''' Randomly sets colors, changes color after repeat ms 
        Will stop after a specified number of ms'''
    colorsOn = []
    colorsOff = []

    for colorChannel in ALL_COLOR_CHANNELS:
        coinToss = random.randint(0,1)
        if coinToss == 0:
            colorsOff.append(colorChannel)
        else:
            colorsOn.append(colorChannel)

    print "Setting OFF on channels", colorsOff
    print "(Autorender) Setting ON on channels", colorsOn
    dmx.setChannel(colorsOff, 0)
    dmx.setChannel(colorsOn, 255, autorender=True)

    if event["stopTime"] != None and datetime.datetime.now() < event["stopTime"]:
        event["time"] = datetime.datetime.now() + datetime.timedelta(milliseconds = event["repeatMs"])
        with gEventQueueLock:
            eventQueue.append(event)
        sortEventQueue()
    else:
        resumeHeartBeats()

# XXX FIXME - WE HAVE TWO FTDI DEVICES ON THIS THING. WE CANNOT MAKE ASSUMPTIONS ABOUT WHICH IS
# THE ENTEC AND WHICH IS THE HEART CONTROL BOX. NEED TO INTERREGATE THE USB DEVICE
def initDMX():
    print "Init DMX!"
    for filename in os.listdir("/dev"):
        if filename.startswith("tty.usbserial"):  # this is the ftdi usb cable on the Mac
            print "Dmx uses connection", filename
            return pysimpledmx.DMXConnection("/dev/" + filename)
        elif filename.startswith("ttyUSB1"):      # this is the ftdi usb cable on the Pi (Linux Debian)
            print "Dmx uses connection", filename
            return pysimpledmx.DMXConnection("/dev/" + filename)
    print "No available dmx controllers"
    return None

def main(args):
    global eventQueue
    global dmx
    global gReceiverId
    global gNextHeartBeat

    running = True
    dmx = initDMX()
    print "Dmx returns", dmx
    heartBeatListener = createBroadcastListener(HEARTBEAT_PORT)
    commandListener   = createBroadcastListener(COMMAND_PORT)
    eventQueue = []

    if len(args) > 1:
        gReceiverId = int(args[1])

    try:
        while (running):
            readfds = [heartBeatListener, commandListener]
            if not eventQueue:
                if gNextHeartBeat == None:
                    print "no gNextHeartBeat"
                #print "Setting all red channels OFF"
                #dmx.setChannel(ALL_RED_CHANNELS, 0)
                #if allowSingleColor:
                #    print "No heartbeat - Setting all white channels ON, autorender"
                #    dmx.setChannel(ALL_WHITE_CHANNELS, 255, autorender = True)

                inputReady, outputReady, exceptReady = select(readfds, [], [])
            else:
                with gEventQueueLock:
                    waitTime = (eventQueue[len(eventQueue)-1]["time"] - datetime.datetime.now()).total_seconds()
                waitTime = max(waitTime, 0)
                inputReady, outputReady, exceptReady = select(readfds, [], [], waitTime)

            if inputReady:
                for fd in inputReady:
                    if fd is heartBeatListener:
                        heartBeatData = fd.recv(1024)
                        handleHeartBeatData(heartBeatData)
                    elif fd is commandListener:
                        commandData = fd.recv(2014)
                        handleCommandData(commandData)
            renderEvents()

        dmx.close()
        heartBeatListener.close()
        commandListener.close()
        print "Shutdown!"

    except KeyboardInterrupt:
        print "CLOSING"
        dmx.close()
        running = False
        heartBeatListener.close()
        commandListener.close()

if __name__ == '__main__':
    main(sys.argv)
    

