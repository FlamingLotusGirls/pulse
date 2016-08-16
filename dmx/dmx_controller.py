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
import heartbeat
import time

BROADCAST_ADDR = "192.168.1.255"
HEARTBEAT_PORT = 5000
COMMAND_PORT   = 5001
MULTICAST_TTL  = 4
BAUDRATE       = 19200

DMX_ADDRESS = "/dev/tty.usbserial-EN195017"
DMX_RED_CHANNEL = 2
DMX_GREEN_CHANNEL = 3
DMX_BLUE_CHANNEL = 4
DMX_WHITE_CHANNEL = 5
DMX_CHANNEL_COUNT = 6 # Can be 6/7/8/12

running = True
allowHeartBeats = True
currentHeartBeatSource = 0 # ???
dmx = None
previousHeartBeatTime = None
gReceiverId = 4

HEARTBEAT = 1
STROBE     = 2
   # = 3



effects = {HEARTBEAT:[[1,1,0], [2,1,100], [1,0,200], [2,0,300]],
           STROBE:    [[3,1,0], [4,1,100], [5,1,200], [3,0,300], [4,0,400], [5,0,500]]}

class Commands():
    STOP_ALL             = 1
    STOP_HEARTBEAT       = 2
    START_HEARTBEAT      = 3
    START_STROBE         = 4
    STOP_STROBE          = 5
    USE_HEARTBEAT_SOURCE = 6



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
    pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)
    print "before if"
    print pod_id
    print currentHeartBeatSource
    if pod_id is currentHeartBeatSource and allowHeartBeats:
        print "sequenceID", sequenceId
        print "beatIntervalMs", beatIntervalMs
        print "beatOffsetMs", beatOffsetMs
        print "bpmApprox", bpmApprox
        print "timestamp", timestamp
        if previousHeartBeatTime:
            heartBeatStartTime = previousHeartBeatTime + daytime.timedelta(milliseconds = beatIntervalMs)
        else:
            heartBeatStartTime = datetime.datetime.now()

        if heartBeatStartTime <= datetime.datetime.now():
            print "1"
            loadEffect(HEARTBEAT, datetime.datetime.now())
        else:
            print "2 ", heartBeatStartTime
            loadEffect(HEARTBEAT, heartBeatStartTime)

        sortEventQueue()


def handleCommandData(commandData):
    global currentHeartBeatSource
    receiverId, commandTrackingId, commandId = struct.unpack("=BBH", commandData)
    if receiverId is gReceiverId:                  # it's for us!
        if command is Command.STOP_ALL:
            removeAllEffects()
        elif command is STOP_HEARTBEAT:
            stopHeartBeat()
        elif command is START_EFFECT:
            dummy1, dummy2, dummy3, effectId = struct.unpack("=BBHL", commandData)
            loadEffect(effectId, datetime.datetime.now())
        elif command is STOP_EFFECT:
            dummy1, dummy2, dummy3, effectId = struct.unpack("=BBHL", commandData)
            removeEffect(effectId)
        elif command is START_HEARTBEAT:
            allowHeartBeats = True
        elif command is USE_HEARTBEAT_SOURCE:
            dummy1, dummy2, dummy3, pod_id = struct.unpack("=BBHL", commandData)
            currentHeartBeatSource = pod_id

        sortEventQueue()

def stopHeartBeat():
    eventQueue[:] = [e for e in eventQueue if (e.get("effectId") != HEARBTEAT)]
    allowHeartBeats = False

def removeAllEffects():
    eventQueue = []

def loadEffect(effectId, startTime): # TODO: The information we need is heartbear duration
    if effects[effectId] != None:
        for event in effects[effectId]:
            print "event"
            canonicalEvent = {}
            canonicalEvent["effectId"] = effectId
            #print "add event" + str(event)
            # canonicalEvent["controllerId"] = intToHex(event[0]//8)
            # canonicalEvent["channel"]      = event[0] %8
            # canonicalEvent["onOff"]        = event[1]
            canonicalEvent["time"]         = startTime + datetime.timedelta(milliseconds = event[2])
            #print "canonical event is " + str(canonicalEvent)
            #print "timedelta is " + str(datetime.timedelta(milliseconds = event[2]))
            eventQueue.append(canonicalEvent)



def sortEventQueue():
    eventQueue.sort(key=itemgetter("time"), reverse=True)


def renderEvents():
    # print "eventqueue: ", eventQueue
    if len(eventQueue) == 0:
        return
    global dmx
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
        currentEvents.append(event)

    if currentEvents:
        if not dmx:
            dmx = pysimpledmx.DMXConnection(DMX_ADDRESS)
        for event in currentEvents:

            process_heartbeat(event)

def process_heartbeat(event):
    # TODO: Still need to listen to port with select while playing
    # TODO: Also need to figure out timing
    # TODO: Ask carolyn about heartbeat... they seem to discard information about frequency

    # heartbeat.heartbeat1(dmx)
    heartbeat.heartbeat1_5(dmx)


    print "event ", event

    # sys.exit()


if __name__ == '__main__':
    running = True
    dmx = pysimpledmx.DMXConnection(DMX_ADDRESS)
    heartBeatListener = createBroadcastListener(HEARTBEAT_PORT)
    commandListener   = createBroadcastListener(COMMAND_PORT)
    eventQueue = []

    try:
        while (running):
            readfds = [heartBeatListener, commandListener]
            if not eventQueue:
                # TODO: Need way to turn this on and off
                dmx.setChannel([DMX_WHITE_CHANNEL, DMX_WHITE_CHANNEL + DMX_CHANNEL_COUNT], 255, autorender = True)
                inputReady, outputReady, exceptReady = select(readfds, [], [])
            else:
                waitTime = (eventQueue[len(eventQueue)-1]["time"] - datetime.datetime.now()).total_seconds()
                print "!!doing select, timeout is %f" % waitTime
                waitTime = max(waitTime, 0)
                inputReady, outputReady, exceptReady = select(readfds, [], [], waitTime)

            if inputReady:
                dmx.setChannel([DMX_WHITE_CHANNEL, DMX_WHITE_CHANNEL + DMX_CHANNEL_COUNT], 0, autorender = True)
                for fd in inputReady:
                    if fd is heartBeatListener:
                        heartBeatData = fd.recv(1024)
                        handleHeartBeatData(heartBeatData)
                    elif fd is commandListener:
                        commandData = fd.ecv(2014)
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
