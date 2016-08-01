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
           

# Commands
class Commands():
    STOP_ALL             = 1
    STOP_HEARTBEAT       = 2
    START_HEARTBEAT      = 3
    START_EFFECT         = 4
    STOP_EFFECT          = 5
    USE_HEARTBEAT_SOURCE = 6


running = True
allowHeartBeats = True
currentHeartBeatSource = 1
ser = None
previousHeartBeatTime = None
gReceiverId = 0  # XXX need to set the receiver Id, or more properly, the unit id, from a file or something

    

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
    
def handleHeartBeatData(heartBeatData):
	### This structure has to match the one in BPMPulseData_t BPMPulse.h
    pod_id, sequenceId, beatIntervalMs, beatOffsetMs, bpmApprox, timestamp = struct.unpack("=BBHLfL", heartBeatData)
    print "heartbeat pod_id is %d bpm is %d" % (pod_id, bpmApprox) # XXX bps is not what we want. We want bpm.
    if pod_id is currentHeartBeatSource and allowHeartBeats:
        # XXX should use the beatOffset (time lapse since event) 
        # XXX much of current computations done assuming much simpler hb structure - can probably
        # make this all much easier now.
        stopHeartBeat() # XXX should allow the last bit of the heart beat to finish, if we're in the middle
        if previousHeartBeatTime:
#            heartBeatStartTime = previousHeartBeatTime + daytime.timedelta(seconds = 1/(bpm*60))
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
            
        # FIXME !!! schedule heartbeat event after previous one has cleared sorta... XXX do this
        
def sortEventQueue():
    eventQueue.sort(key=itemgetter("time"), reverse=True)

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
        
    # could have a define effect as well... XXX MAYBE
    
def removeEffect(effectId):
    for event in eventQueue:
        if event["effectId"] is effectId:
            eventQueue.remove(event) 
   
hexStr = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]         
def intToHex(myInt):
    if myInt < 0:
        return "0"
    modulus = myInt % 16
    div     = myInt // 16
    
    div = min(15, div)

    return hexStr[div] + hexStr[modulus]


# canonical event is the effectId, the controllerId, the channel, on/off, and the timestamp
def loadEffect(effectId, starttime):
    if effects[effectId] != None:
        for event in effects[effectId]:
            canonicalEvent = {}
            canonicalEvent["effectId"] = effectId
            #print "add event" + str(event)
            canonicalEvent["controllerId"] = intToHex(event[0]//8)
            canonicalEvent["channel"]      = event[0] %8
            canonicalEvent["onOff"]        = event[1]
            canonicalEvent["time"]         = starttime + datetime.timedelta(milliseconds = event[2])
            #print "canonical event is " + str(canonicalEvent)
            #print "timedelta is " + str(datetime.timedelta(milliseconds = event[2]))
            eventQueue.append(canonicalEvent)
        
def removeAllEffects():
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
    # getting all the events we want to get
    currentEvents = []
    currentTime = datetime.datetime.now()
    timewindow = currentTime + datetime.timedelta(milliseconds = 5)
    event = eventQueue.pop()
    while event and event["time"] < timewindow:
        currentEvents.append(event)
        try:
            event = eventQueue.pop()
        except IndexError:
            break
    if event["time"] >= timewindow: 
        eventQueue.append(event)
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

if __name__ == '__main__':
    running = True
    heartBeatListener = createBroadcastListener(HEARTBEAT_PORT)
    commandListener   = createBroadcastListener(COMMAND_PORT)
    ser = initSerial() #XXX need to handle serial disconnect, restart
    eventQueue = [] # NB - don't need a real queue here. Only one thread 
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
        
    

# check for serial connection every so often...
