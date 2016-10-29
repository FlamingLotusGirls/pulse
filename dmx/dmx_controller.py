# Python for controlling the DMX lights according to UDP packets
# Some (most) code was shamelessly stolen from Carolyn Wales

# TODO: Shut off heartbeats when packets aren't being sent in anymore. This is related to using BPM to time heartbeats sine currently excess heartbeats are being put into the queue

import datetime
import os
from operator import itemgetter, attrgetter
from select import select
import serial
import socket
import struct
import sys
import pysimpledmx
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

#running = True
allowHeartBeats = True
allowSingleColor = True
allowStrobing = True
isStrobing = False
dmx = None
eventQueue = None
gReceiverId = 3

HEARTBEAT = 1
STROBE    = 2
SINGLE    = 3

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

gGlobalEffectId = 0

# Effects format ---  EFFECT:[[channels], intensity, duration from start of heartbeat(ms)]
effects = {HEARTBEAT:[[1,100,100], [2,250,150], [1,100,225], [2,180,300], [1,100,350]],
            STROBE:    [[3,1,0], [4,1,100], [5,1,200], [3,0,300], [4,0,400], [5,0,500]]}

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
    if not allowHeartBeats:
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
    dmx.setChannel(ALL_WHITE_CHANNELS, 0)


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
            dmxSingleColor()
        elif commandId is Commands.DMX_STROBE:
            dmxStrobe()
        elif commandId is Commands.USE_HEARTBEAT_SOURCE:
            gCurrentHeartBeatSource = commandData
            print "Received new heartbeat source, is ", gCurrentHeartBeatSource
        sortEventQueue() #Necessary?

def dmxStrobe():
    global isStrobing
    global allowHeartBeats

    if isStrobing:
        removeEffect(STROBE)
        print "Setting all color channels OFF, autorender"
        dmx.setChannel(ALL_RED_CHANNELS + ALL_GREEN_CHANNELS +
                    ALL_BLUE_CHANNELS, 0, autorender=True)
        isStrobing = False
        return

    # Not strobing, so add strobe to eventQueue
    removeEffect(HEARTBEAT)
    allowHeartBeats = False
    print "Setting all white channels ON"
    dmx.setChannel(ALL_WHITE_CHANNELS, 0)
    loadEffect(STROBE, datetime.datetime.now(), 300)

def dmxSingleColor():
    global allowSingleColor
    allowSingleColor =  not allowSingleColor

    if allowSingleColor:
        removeEffect(HEARTBEAT)
        removeEffect(STROBE)
        print "Single color - Setting all white channels ON, autorender"
        dmx.setChannel(ALL_WHITE_CHANNELS, 255, autorender=True)
    else:
        print "Setting all white channels OFF, autorender"
        dmx.setChannel(ALL_WHITE_CHANNELS, 0, autorender=True)

def stopHeartBeat():
    global allowHeartBeats
    global eventQueue
    eventQueue[:] = [e for e in eventQueue if (e.get("effectId") != HEARBTEAT)]
    allowHeartBeats = False

def removeEffect(effectId):
    global eventQueue
    eventQueue[:] = [e for e in eventQueue if (e.get("effectId") == effectId)]

def removeEffectInstance(instanceId):
    global eventQueue
    if not instanceId:
        return

    eventQueue[:] = [e for e in eventQueue if (e.get("globalId") != instanceId)]


def removeAllEffects():
    global eventQueue
    eventQueue = []

def loadEffect(effectId, startTime, repeatMs=0): # TODO: The information we need is heartbeat duration
    ''' Queue up an effect. There can be only a single one-shot effect in the 
        queue at a time, but there can be multiple repeating effects (Although in practice,
        the only repeating effect is the heartbeat) '''
    global gGlobalEffectId
    
    if repeatMs != 0 and effectId != HEARTBEAT:
        removeEffect(effectId)

    firstEffectId = gGlobalEffectId

    if effectId is HEARTBEAT:
        index = 0
        nEvents = len(effects[effectId])
        for eventSection in effects[effectId]:
            event = {}
            event["effectId"] = effectId
            event["globalId"] = gGlobalEffectId
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
            eventQueue.append(event)
        gGlobalEffectId += 1
    elif effectId is STROBE:
        event = {}
        event["effectId"] = effectId
        event["time"]     = startTime
        event["repeatMs"] = repeatMs
        eventQueue.append(event)

    return firstEffectId


def sortEventQueue():
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
        for event in currentEvents:
            if event["effectId"] == HEARTBEAT:
                processHeartbeat(event)
            elif event["effectId"] is STROBE:
                processStrobe(event)
                
            if event["globalId"] == gNextHeartBeat:
                gCurrentHeartBeat = event["globalId"]
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
                    instanceId = loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"]) # XXX what thread is this normally called from?

                if instanceId != None:
                    #print "Auto schedule instance ", instanceId
                    sortEventQueue()            
                    
                    
def processHeartbeat(event):
    global dmx
    if not allowHeartBeats:
        return

    heartbeatSection = effects[HEARTBEAT][event["sectionIndex"]]

    print "(Autorender) Setting all red channels to ", heartbeatSection[1]
    dmx.setChannel(ALL_RED_CHANNELS, heartbeatSection[1], autorender=True)

def processStrobe(event):
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

    event["time"] = datetime.datetime.now() + datetime.timedelta(milliseconds = event["repeatMs"])
    eventQueue.append(event)
    sortEventQueue()

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
                print "Setting all red channels OFF"
                dmx.setChannel(ALL_RED_CHANNELS, 0)
                if allowSingleColor:
                    print "No heartbeat - Setting all white channels ON, autorender"
                    dmx.setChannel(ALL_WHITE_CHANNELS, 255, autorender = True)

                inputReady, outputReady, exceptReady = select(readfds, [], [])
            else:
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
