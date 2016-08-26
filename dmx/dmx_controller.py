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

DMX_RED_CHANNEL   = 2
DMX_GREEN_CHANNEL = 3
DMX_BLUE_CHANNEL  = 4
DMX_WHITE_CHANNEL = 5
DMX_CHANNEL_COUNT = 6 # Can be 6/7/8/12

ALL_RED_CHANNELS = [DMX_RED_CHANNEL, DMX_RED_CHANNEL + DMX_CHANNEL_COUNT,\
                    DMX_RED_CHANNEL + 2 * DMX_CHANNEL_COUNT, \
                    DMX_RED_CHANNEL + 3 * DMX_CHANNEL_COUNT]

ALL_GREEN_CHANNELS = map(lambda x: x+(DMX_GREEN_CHANNEL-DMX_RED_CHANNEL), ALL_RED_CHANNELS)
ALL_BLUE_CHANNELS = map(lambda x: x+(DMX_BLUE_CHANNEL-DMX_RED_CHANNEL), ALL_RED_CHANNELS)
ALL_WHITE_CHANNELS = map(lambda x: x+(DMX_WHITE_CHANNEL-DMX_RED_CHANNEL), ALL_RED_CHANNELS)
ALL_COLOR_CHANNELS = ALL_RED_CHANNELS + ALL_GREEN_CHANNELS + ALL_BLUE_CHANNELS

running = True
allowHeartBeats = True
allowSingleColor = True
allowStrobing = True
isStrobing = False
currentHeartBeatSource = 0 # ???
dmx = None
heartBeatListener = None
commandListener   = None
eventQueue = None
gReceiverId = 3

HEARTBEAT = 1
STROBE    = 2
SINGLE    = 3

gCurrentHeartBeat  = None
gNextHeartBeat     = None
gNextNextHeartBeat = None
gNextHeartBeatStartTime     = 0
gNextNextHeartBeatStartTime = 0

gGlobalEffectId = 0

# Effects format ---  EFFECT:[[channels], intensity, duration from start of heartbeat(ms)]
effects = {HEARTBEAT:[[1,100,100], [2,250,150], [1,100,225], [2,180,300], [1,100,350]],
            STROBE:    [[3,1,0], [4,1,100], [5,1,200], [3,0,300], [4,0,400], [5,0,500]]}

# {HEARTBEAT:[[1,100,100], [2,250,200], [1,80,300], [2,180,400], [1,100,500]],

# {HEARTBEAT:[[1,100,100], [2,250,150], [1,80,275], [2,180,400], [1,100,450]],

# {HEARTBEAT:[[1,100,100], [2,250,150], [1,100,225], [2,180,300], [1,100,350]],


def createBroadcastListener(port, addr=BROADCAST_ADDR):
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
    global allowHeartBeats
    if not allowHeartBeats:
        return

    pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)

    if pod_id is currentHeartBeatSource and allowHeartBeats and beatIntervalMs > 0:

        if beatOffsetMs < beatIntervalMs:
            heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - beatOffsetMs)
        else:
            heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - (beatOffsetMs % beatIntervalMs))

        instanceId = loadEffect(HEARTBEAT, heartBeatStartTime, beatIntervalMs)

        processNextHeartBeat(instanceId, heartBeatStartTime)

        sortEventQueue()


def processNextHeartBeat(instanceId, heartBeatStartTime):
    global gNextHeartBeat
    global gNextNextHeartBeat
    global gNextHeartBeatStartTime
    global gNextNextHeartBeatStartTime

    if gNextHeartBeat == None or gNextHeartBeatStartTime > heartBeatStartTime:
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

    dmx.setChannel(ALL_WHITE_CHANNELS, 0)


def handleCommandData(commandData):
    global currentHeartBeatSource
    global allowHeartBeats
    global allowSingleColor
    global isStrobing
    # TODO: There is a new command format
    receiverId, commandTrackingId, commandId, commandData = struct.unpack("=BBHI", commandData)
    if receiverId is gReceiverId:                  # it's for us!
        if commandId is Command.STOP_ALL:
            allowHeartBeats = False
            allowSingleColor = False
            isStrobing = False
            removeAllEffects()
        elif commandId is Command.STOP_HEARTBEAT:
            stopHeartBeat()
        elif commandId is Command.START_HEARTBEAT:
            allowHeartBeats = True
        elif commandId is Command.DMX_SINGLE_COLOR:
            dmxSingleColor()
        elif commandId is Command.DMX_STROBE:
            dmxStrobe()
        elif commandId is Command.USE_HEARTBEAT_SOURCE:
            dummy1, dummy2, dummy3, pod_id = struct.unpack("=BBHL", commandData)
            currentHeartBeatSource = pod_id

        sortEventQueue() #Necessary?

def dmxStrobe():
    global isStrobing
    global allowHeartBeats

    if isStrobing:
        removeEffect(STROBE)
        dmx.setChannel(ALL_RED_CHANNELS + ALL_GREEN_CHANNELS +
                    ALL_BLUE_CHANNELS, 0, autorender=True)
        isStrobing = False
        return

    # Not strobing, so add strobe to eventQueue
    removeEffect(HEARTBEAT)
    allowHeartBeats = False
    dmx.setChannel(ALL_WHITE_CHANNELS, 0)
    loadEffect(STROBE, datetime.datetime.now(), 300)

def dmxSingleColor():
    global allowSingleColor
    allowSingleColor =  not allowSingleColor

    if allowSingleColor:
        removeEffect(HEARTBEAT)
        removeEffect(STROBE)
        dmx.setChannel(ALL_WHITE_CHANNELS, 255, autorender=true)
    else:
        dmx.setChannel(ALL_WHITE_CHANNELS, 0, autorender=true)

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
    global gGlobalEffectId
    if repeatMs != 0 and effectId != HEARTBEAT:
        removeEffect(effectId)


    firstEffectId = gGlobalEffectId

    if effectId is HEARTBEAT:
        index = 0
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
                event["repeatMs"] = repeatMs
                event["nextStartTime"] = startTime + datetime.timedelta(milliseconds = repeatMs)
            else:
                # TODO: Still need to figure out times for each event
                event["time"] = startTime + datetime.timedelta(milliseconds = 1000)
            eventQueue.append(event)
            gGlobalEffectId += 1

        return firstEffectId
    elif effectId is STROBE:
        event = {}
        event["effectId"] = effectId
        event["time"] = startTime
        event["repeatMs"] = repeatMs
        eventQueue.append(event)


def sortEventQueue():
    eventQueue.sort(key=itemgetter("time"), reverse=True)


def renderEvents():
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
        sortEventQueue()

    if currentEvents:
        if not dmx:
            dmx = initDMX()
        for event in currentEvents:
            if event["effectId"] == HEARTBEAT:
                processHeartbeat(event)
            elif event["effectId"] is STROBE:

                processStrobe(event)

def processHeartbeat(event):
    global dmx
    if not allowHeartBeats:
        return

    heartbeatSection = effects[HEARTBEAT][event["sectionIndex"]]

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

    dmx.setChannel(colorsOff, 0)
    dmx.setChannel(colorsOn, 255, autorender=True)

    event["time"] = datetime.datetime.now() + datetime.timedelta(milliseconds = event["repeatMs"])
    eventQueue.append(event)
    sortEventQueue()

# XXX FIXME - WE HAVE TWO FTDI DEVICES ON THIS THING. WE CANNOT MAKE ASSUMPTIONS ABOUT WHICH IS
# THE ENTEC AND WHICH IS THE HEART CONTROL BOX. NEED TO INTERREGATE THE USB DEVICE
def initDMX():
    for filename in os.listdir("/dev"):
        if filename.startswith("tty.usbserial"):  # this is the ftdi usb cable on the Mac
            return pysimpledmx.DMXConnection("/dev/" + filename)
        elif filename.startswith("ttyUSB1"):      # this is the ftdi usb cable on the Pi (Linux Debian)
            return pysimpledmx.DMXConnection("/dev/" + filename)
    return None

def main(args):
    global gReceiverId
    running = True
    dmx = initDMX()
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
                dmx.setChannel(ALL_RED_CHANNELS, 0)
                if allowSingleColor:
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


    except KeyboardInterrupt:
        print "CLOSING"
        dmx.close()
        running = False
        heartBeatListener.close()
        commandListener.close()

if __name__ == '__main__':
    main(sys.argv)
