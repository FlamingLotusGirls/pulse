# Python for controlling the DMX lights according to UDP packets
# Some (most) code was shamelessly stolen from Carolyn Wales

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
CHASE     = 2
ALLPOOF   = 3

effects = {HEARTBEAT:[[1,1,0], [2,1,100], [1,0,200], [2,0,300]],
           CHASE:    [[3,1,0], [4,1,100], [5,1,200], [3,0,300], [4,0,400], [5,0,500]],
           ALLPOOF:  [[3,1,0], [4,1,0],   [5,1, 0],  [3,0,700], [4,0,700], [5,0,700]]}

class Commands():
    STOP_ALL             = 1
    STOP_HEARTBEAT       = 2
    START_HEARTBEAT      = 3
    START_EFFECT         = 4
    STOP_EFFECT          = 5
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
            allowHeartBeats = False
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

hexStr = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
def intToHex(myInt):
    if myInt < 0:
        return "0"
    modulus = myInt % 16
    div     = myInt // 16

    div = min(15, div)

    return hexStr[div] + hexStr[modulus]

def loadEffect(effectId, startTime): # TODO: The information we need is heartbear duration
    if effects[effectId] != None:
        for event in effects[effectId]:
            print "event"
            canonicalEvent = {}
            canonicalEvent["effectId"] = effectId
            #print "add event" + str(event)
            canonicalEvent["controllerId"] = intToHex(event[0]//8)
            canonicalEvent["channel"]      = event[0] %8
            canonicalEvent["onOff"]        = event[1]
            canonicalEvent["time"]         = startTime + datetime.timedelta(milliseconds = event[2])
            #print "canonical event is " + str(canonicalEvent)
            #print "timedelta is " + str(datetime.timedelta(milliseconds = event[2]))
            eventQueue.append(canonicalEvent)


def sortEventQueue():
    eventQueue.sort(key=itemgetter("time"), reverse=True)


def renderEvents():
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
            pass
            # dmx = pysimpledmx.DMXConnection(DMX_ADDRESS)
        for event in currentEvents:
            heartbeat(event)

def heartbeat(event):
    # pattern of a heartbeat divided in 10
    # 1: flat
    # 2: small bump
    # 3: flat, then small down
    # 4: big up, then bigger down
    # 5: back to normal, then flat
    # 6: small (slightly larger) bump
    # 7: flat
    #
    # flat: 100
    # 1: 100
    # 2: 100->120->100
    # 3: 100->100->80
    # 4: 80->250->60
    # 5: 60->100->100
    # 6: 100->130->100
    # 7: 100

    # TODO: Ask carolyn about heartbeat... they seem to discard information about frequency

    print "event ", event

    now = datetime.datetime.now()
    timeWindow = now + datetime.timedelta(milliseconds = 1000)
    seventh = (1000//7)/1000.0

    dmx.setChannel(DMX_RED_CHANNEL, 100)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    dmx.render()
    time.sleep(seventh + (seventh / 3))
    dmx.setChannel(DMX_RED_CHANNEL, 120)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 120)
    dmx.render()
    time.sleep(seventh/3)
    dmx.setChannel(DMX_RED_CHANNEL, 100)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    dmx.render()
    time.sleep(seventh)
    dmx.setChannel(DMX_RED_CHANNEL, 80)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 80)
    dmx.render()
    time.sleep((seventh/3)*2)
    dmx.setChannel(DMX_RED_CHANNEL, 200)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 250)
    dmx.render()
    time.sleep(seventh/3)
    dmx.setChannel(DMX_RED_CHANNEL, 60)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 60)
    dmx.render()
    time.sleep((seventh/3)*2)
    dmx.setChannel(DMX_RED_CHANNEL, 100)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    dmx.render()
    time.sleep(seventh)
    dmx.setChannel(DMX_RED_CHANNEL, 130)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 130)
    dmx.render()
    time.sleep(seventh/3)
    dmx.setChannel(DMX_RED_CHANNEL, 100)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    dmx.render()
    time.sleep((seventh/3)*2)



    # while now < timeWindow:
    #     if (now + datetime.timedelta(milliseconds = seventh)) < timeWindow:
    #         dmx.setChannel(DMX_RED_CHANNEL, 100)
    #         dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    #         dmx.render()




    now = datetime.datetime.now()


    dmx.setChannel(DMX_RED_CHANNEL, 100)
    dmx.setChannel(DMX_GREEN_CHANNEL+12, 200)
    dmx.render()
    time.sleep(0.2)
    for i in range(20):
        dmx.setChannel(DMX_RED_CHANNEL, 100 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100-i)
        dmx.render()
        time.sleep(0.001)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    for i in range(85):
        dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
        dmx.render()
        time.sleep(0.001)
    for i in range(75):
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
        dmx.render()
        time.sleep(0.001)
    print "difference1 = ", (datetime.datetime.now() - now)
    time.sleep(1)

    for i in range(20):
        dmx.setChannel(DMX_RED_CHANNEL, 100 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100-i)
        dmx.render()
        time.sleep(0.001)
    dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    for i in range(85):
        dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
        dmx.render()
        time.sleep(0.001)
    for i in range(75):
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
        dmx.render()
        time.sleep(0.001)
    time.sleep(1)

    for i in range(20):
        dmx.setChannel(DMX_RED_CHANNEL, 100 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 - i)
        dmx.render()
        time.sleep(0.001)
    for i in range(85):
        dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
        dmx.render()
        time.sleep(0.001)
    for i in range(75):
        dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
        dmx.render()
        time.sleep(0.001)
    time.sleep(1)
    now = datetime.datetime.now()
    for i in range(20):
        dmx.setChannel(DMX_RED_CHANNEL, 100 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 - i)
        dmx.render()
        time.sleep(0.001)
    for i in range(85):
        dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
        dmx.render()
        time.sleep(0.001)
    for i in range(75):
        dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
        dmx.render()
        time.sleep(0.002)
    for i in range(100):
        dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
        dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
        dmx.render()
        time.sleep(0.001)
    print "difference2 = ", (datetime.datetime.now() - now)

    sys.exit()



    # for i in range(90):
    #     dmx.setChannel(DMX_RED_CHANNEL, 200 - i*2)
    #     dmx.render()
    #     time.sleep(0.005)
    # dmx.setChannel(DMX_RED_CHANNEL, 200)
    # dmx.render()
    # time.sleep(0.2)
    # for i in range(90):
    #     dmx.setChannel(DMX_RED_CHANNEL, 200 - i*2)
    #     dmx.render()
    #     time.sleep(0.005)

    if now > timeWindow:
        print "ALREADY PAST TIME WINDOW"
    while now < timeWindow:
        for j in range(125):
            dmx.setChannel(DMX_RED_CHANNEL, 255-(2*j))
            dmx.render()
            time.sleep(0.001)
        dmx.setChannel(DMX_RED_CHANNEL, 255)
        dmx.render()
        time.sleep(2)
        sys.exit()






if __name__ == '__main__':
    running = True
    dmx = pysimpledmx.DMXConnection(DMX_ADDRESS)
    heartBeatListener = createBroadcastListener(HEARTBEAT_PORT)
    commandListener   = createBroadcastListener(COMMAND_PORT)
    eventQueue = []
    print datetime.datetime.now()
    print datetime.datetime.now()
    print datetime.datetime.now()
    print datetime.datetime.now()


    try:
        while (running):
            readfds = [heartBeatListener, commandListener]
            if not eventQueue:
                inputReady, outputReady, exceptReady = select(readfds, [], [])
            else:
                waitTime = (eventQueue[len(eventQueue)-1]["time"] - datetime.datetime.now()).total_seconds()
                print "!!doing select, timeout is %f" % waitTime
                waitTime = max(waitTime, 0)
                inputReady, outputReady, exceptReady = select(readfds, [], [], waitTime)

            if inputReady:
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
            # dmx.setChannel(DMX_RED_CHANNEL, 255)
            # dmx.render()
            # for j in range(150):
            #     dmx.setChannel(DMX_RED_CHANNEL, 255-j)
            #     dmx.render()
            #     time.sleep(0.05)
            # dmx.setChannel(DMX_RED_CHANNEL, 255)
            # dmx.render()



        # for i in range(254):
        #     # dmx.setChannel(1, 0)
        #     dmx.setChannel(DMX_RED_CHANNEL, 255)
        #     dmx.render()
        #     for j in range(150):
        #         dmx.setChannel(DMX_RED_CHANNEL, 255-j)
        #         dmx.render()
        #         time.sleep(0.05)
        #     dmx.setChannel(DMX_RED_CHANNEL, 255)
        #     dmx.render()
            # dmx.setChannel(6, i)
            # dmx.setChannel(DMX_GREEN_CHANNEL, i)   # set DMX channel 3 to 0
            # dmx.setChannel(DMX_BLUE_CHANNEL, i)
            # dmx.setChannel(255-i, 255)
            # dmx.setChannel(i+2, 255)
            # dmx.setChannel(i+2, 255)
            # print "channel = ", i
            # dmx.setChannel(7, i)
            # time.sleep(0.05)

    except KeyboardInterrupt:
        print "CLOSING"
        dmx.close()
        running = False
        heartBeatListener.close()
        commandListener.close()
