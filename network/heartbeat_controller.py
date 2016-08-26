# Heart Fire controller
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
import os
from operator import itemgetter, attrgetter
from select import select
import serial
import socket
import struct
import sys
from commands import *

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


running = True
heartBeatListener = None
commandListener   = None
ser = None #XXX need to handle serial disconnect, restart
eventQueue = None # NB - don't need a real queue here. Only one thread
allowHeartBeats = True
currentHeartBeatSource = 0
ser = None
previousHeartBeatTime = None
gReceiverId = 0
gCurrentHeartBeat  = None
gNextHeartBeat     = None
gNextNextHeartBeat = None
gNextHeartBeatStartTime     = 0
gNextNextHeartBeatStartTime = 0

gGlobalEffectId    = 0



# XXX - since we're using a list, we probably want to be pulling off the end of the list
# rather than the beginning. XXX TODO


def createBroadcastListener(port, addr=BROADCAST_ADDR):
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
#    sock.bind((addr, port))
    sock.bind(('', port))

#    # Set some more multicast options
#    mreq = struct.pack("=4sl", socket.inet_aton(addr), socket.INADDR_ANY)
#    sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    return sock

# And we need to generate another heart beat if I dont hear one... XXX
def handleHeartBeatData(heartBeatData):
	### This structure has to match the one in BPMPulseData_t BPMPulse.h
    pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)
    print "heartbeat pod_id is %d bpm is %d" % (pod_id, bpmApprox)
    if pod_id is currentHeartBeatSource and allowHeartBeats and bpmApprox != 0 and beatIntervalMs > 0:
#        stopHeartBeat() # XXX should allow the last bit of the heart beat to finish, if we're in the middle

        if beatOffsetMs < beatIntervalMs: # if we haven't already missed the 'next' beat...
            heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - beatOffsetMs)
        else:
            heartBeatStartTime = datetime.datetime.now() + datetime.timedelta(milliseconds = beatIntervalMs - (beatOffsetMs % beatIntervalMs))

        #if previousHeartBeatTime:
        #    heartBeatStartTime = previousHeartBeatTime + datetime.timedelta(milliseconds = beatIntervalMs)
        #else:
        #    heartBeatStartTime = datetime.datetime.now()

        # schedule next heart beat
        instanceId = loadEffect(HEARTBEAT, heartBeatStartTime, beatIntervalMs)

        # fix up additional heart beats already in the queue
        # if there's already a next heart beat, and the start time is *greater than* the incoming time, kill it
        helper_addHBReference(instanceId, heartBeatStartTime)

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

        sortEventQueue()

def helper_addHBReference(instanceId, heartBeatStartTime):
    global gNextHeartBeat
    global gNextHeartBeatStartTime
    global gNextNextHeartBeat
    global gNextNextHeartBeatStartTime

    print "adding reference for ", instanceId

    if (gNextHeartBeat == None or (gNextHeartBeat != None and gNextHeartBeatStartTime > heartBeatStartTime)):
        print "new heart beat replaces previous"
        # replace gNextHeartBeat
        removeEffectInstance(gNextHeartBeat)
        gNextHeartBeat = instanceId
        gNextHeartBeatStartTime = heartBeatStartTime
        # nuke NextNextHeartBeat
        removeEffectInstance(gNextNextHeartBeat)
        gNextNextHeartBeat = None
    else:
        # replaceNextNextHeartBeat
        if gNextNextHeartBeat != None:
            removeEffectInstance(gNextNextHeartBeat)
        gNextNextHeartBeat = instanceId
        gNextNextHeartBeatStartTime = heartBeatStartTime

    print "Next hbId is ", gNextHeartBeat
    print "NextNext hbId is ", gNextNextHeartBeat


def sortEventQueue():
    eventQueue.sort(key=itemgetter("time"), reverse=True)

def handleCommandData(commandData):
    global currentHeartBeatSource
    receiverId, commandTrackingId, commandId, data = struct.unpack("=BBHL", commandData)
    if receiverId is gReceiverId  or receiverId is ALL_LISTENERS: # it's for us!
        if commandId is Command.STOP_ALL:
            removeAllEffects()
        elif commandId is Command.STOP_HEARTBEAT:
            allowHeartBeats = False
            stopHeartBeat()
#        elif commandId is Command.START_EFFECT:
#            dummy1, dummy2, dummy3, effectId = struct.unpack("=BBHL", commandData)
#            loadEffect(effectId, datetime.datetime.now())
#        elif commandId is Command.STOP_EFFECT:
#            dummy1, dummy2, dummy3, effectId = struct.unpack("=BBHL", commandData)
#            removeEffect(effectId)
        elif commandId is Command.START_HEARTBEAT:
            allowHeartBeats = True
        elif commandId is Command.USE_HEARTBEAT_SOURCE:
#            dummy1, dummy2, dummy3, pod_id = struct.unpack("=BBHL", commandData)
            currentHeartBeatSource = data

        sortEventQueue()

    # could have a define effect as well... XXX MAYBE

def removeEffect(effectId):
    print "removing effect ", effectId
    for event in eventQueue:
        if event["effectId"] is effectId:
            eventQueue.remove(event)

def removeEffectInstance(instanceId):
    print "removing instance", instanceId
    if instanceId == None:
        return

    for event in eventQueue:
        print "  found event", event
        if event["globalId"] == instanceId:
            print "   removing an event", event
            eventQueue.remove(event)

hexStr = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
def intToHex(myInt):
    if myInt < 0:
        return "0"
    modulus = myInt % 16
    div     = myInt // 16

    div = min(15, div)

    return hexStr[div] + hexStr[modulus]


# canonical event is the effectId, the globalEffectId, the controllerId, the channel, on/off, the timestamp,
# and the interval at which to repeat the effect.
# Note that the effectId is which *type* of effect. The globalEffectId is a unique id for an effect instance
def loadEffect(effectId, starttime, repeatMs=0):
    global gGlobalEffectId
    # NB - repeating events are special, because they automatically schedule themselves.
    # Only one of a particular type is allowed to be in the queue at a time, so if
    # there is already one, delete it.
    if repeatMs != 0 and effectId != HEARTBEAT:
        removeEffect(effectId)

    # Now set up the event queue with the events in this effect
    if effects[effectId] != None:
        globalId = gGlobalEffectId
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

            eventQueue.append(canonicalEvent)
            eventIdx += 1
        gGlobalEffectId += 1

    return globalId

def removeAllEffects():
    global eventQueue
    eventQueue = []

def stopHeartBeat():
    removeEffect(HEARTBEAT)

def initSerial():
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



def createEventString(events):
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


def sendEvents():
    if (len(eventQueue)==0):
        return
    global ser
    global gCurrentHeartBeat
    global gNextHeartBeat
    global gNextHeartBeatStartTime
    global gNextNextHeartBeat
    global gNextNextHeartBeatStartTime

    # getting all the events we want to get
    currentEvents = []
    currentTime = datetime.datetime.now()
    timewindow = currentTime + datetime.timedelta(milliseconds = 5)
    #print "timewindow is ", timewindow
    #print "currentTime is ", currentTime
    event = eventQueue.pop()
    while event and event["time"] < timewindow:
        #print "Adding event with time ", event["time"]
        currentEvents.append(event)
        try:
            event = eventQueue.pop()
        except IndexError:
            break
    if event["time"] >= timewindow:
        eventQueue.append(event)  # XXX is this going to go on the correct side of the queue?
    if currentEvents:
        currentEvents.sort(key=itemgetter("controllerId"))
        eventString = createEventString(currentEvents)
        print "Event string is %s" %eventString
        if not ser:
            ser = initSerial()
        if ser:
            try:
                ser.write(eventString.encode())   # XXX what are all the ways this might fail?
            except IoException:
                ser.close()
                ser = None
        for event in currentEvents:
            # if we're starting a heartbeat, reset the pointers to current, next, and next next heartbeat ids
            print "playing effect instance ", event["globalId"]
            print "nextHeartBeat is ", gNextHeartBeat
            if event["globalId"] == gNextHeartBeat:
                gCurrentHeartBeat = event["globalId"]
                gNextHeartBeat = gNextNextHeartBeat
                gNextHeartBeatStartTime = gNextNextHeartBeatStartTime
                gNextNextHeartBeat = None
                print "Starting heart beat ", gCurrentHeartBeat
                print "Next beat is ", gNextHeartBeat
            # if we're ending a heartbeat, load up the next one and reset pointers...
            if event["repeatMs"] != 0:
                instanceId = None
                if (event["effectId"] == HEARTBEAT):
                    gCurrentHeartBeat = None
                    if (gNextHeartBeat == None):
                        instanceId = loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"])
                        helper_addHBReference(instanceId, event["nextStartTime"])
                else:
                    instanceId = loadEffect(event["effectId"], event["nextStartTime"], event["repeatMs"]) # XXX what thread is this normally called from?

                if instanceId != None:
                    print "Auto schedule instance ", instanceId
                    sortEventQueue()
                

def main(args):
    global running
    global heartBeatListener
    global commandListener
    global ser
    global eventQueue
    global gReceiverId
    running = True
    heartBeatListener = createBroadcastListener(HEARTBEAT_PORT)
    commandListener   = createBroadcastListener(COMMAND_PORT)
    ser = initSerial() #XXX need to handle serial disconnect, restart
    eventQueue = [] # NB - don't need a real queue here. Only one thread
    
    if len(args) > 1:
        gReceiverId = int(args[1])
        
    print "gReceiverId is ", gReceiverId
    try:
        while (running):
            readfds = [heartBeatListener, commandListener]
            if not eventQueue:
                print "doing select, no timeout"
                inputReady, outputReady, exceptReady = select(readfds, [], [])
            else:
                waitTime = (eventQueue[len(eventQueue)-1]["time"] - datetime.datetime.now()).total_seconds()
                print "!!doing select, timeout is %f" % waitTime
                waitTime = max(waitTime, 0)
                inputReady, outputReady, exceptReady = select(readfds, [], [], waitTime)
            if inputReady:
                print "Have data to read"
                for fd in inputReady:
                    if fd is heartBeatListener:
                        print "received heartbeat"
                        heartBeatData = fd.recv(1024)
                        handleHeartBeatData(heartBeatData)
                    elif fd is commandListener:
                        print "received command"
                        commandData = fd.recv(1024)
                        handleCommandData(commandData)
            sendEvents()

    except KeyboardInterrupt: # need something besides a keyboard interrupt to stop? or not?XXX
        print "Keyboard interrupt detected, terminating"
        running = False
        heartBeatListener.close()
        commandListener.close()

if __name__ == '__main__':
    main(sys.argv)


# heart beat comes in... scheduled for .8 seconds in future... new heart beat comes in... removes
# old heart beat... fail fail fail. Okay, so again, you're allowed to have two in the queue, provided
# that the new one is older than the next one. Same issue that I had for audio.
# So. New event
# go through event queue. first event you find, check time. If time is *after* new event, remove event from queue
# damn and I need an effect instance id for the event, since its now associated with an effect instance
# continue through queue.
# currentheartbeat - currently doing its thing. Never touch
# nextheartbeat - next scheduled heartbeat. Pointer to.
# nextnextheartbeat - heartbeat after the next one.

# check for serial connection every so often...
# rule on the event queue stuff:
# -- when I do a heartbeat, check to see if there is another heartbeat already in the queue
#    if there is, do nothing
#    if there is not, set up a new heartbeat based on the bpm received previously
# -- when I get a new heartbeat, check to see if there is another heartbeat already in the queue
#    if there is, remove it and replace with this new one
# Is that going to work? There was something special about how I had to handle the audio cases....
