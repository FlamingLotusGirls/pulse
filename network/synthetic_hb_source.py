# Simulated heartbeat server
# Get heartbeat rate from web interface (rather than device), send via broadcast
# (Could change this to get heartbeat rate from dial, but for now...)

import BaseHTTPServer
import Queue
import datetime
import socket
import struct
from threading import Thread
import time
from select import select
from commands import *

from cgi import parse_header, parse_multipart
from sys import version as python_version
if python_version.startswith('3'):
    from urllib.parse import parse_qs
else:
    from urlparse import parse_qs

# some globals - for the moment XXX
heartBeatSender      = None
commandSender        = None
running              = True

gReceiverId = 0 # We are the synthetic heartbeat. 

BROADCAST_ADDR ="192.168.1.255"
HEARTBEAT_PORT = 5000
COMMAND_PORT   = 5001
MULTICAST_TTL  = 4

ALL_LISTENERS = 255

# XXX TODO - handle network down errors. If the network is down, just continue...

# XXX have not tested this against Python 3
# XXX do not have a running flag that I can use to shut down the threads

# XXX this class is probably going to be used by many bits and pieces - externalize
# it
class HeartBeatSender():
    def __init__(self, heartBeatId=0):
        self.heartBeatId = heartBeatId
        self.heartBeatSignalQueue = Queue.Queue()
        self.heartBeatSendingThread = HeartBeatSender.HeartBeatSendingThread(self.heartBeatSignalQueue)
        self.heartBeatSendingThread.start()
        
    def setHeartBeatFrequency(self, frequency):
        self.heartBeatSignalQueue.put({"frequency": frequency}) 
        
    def close(self):
        self.heartBeatSignalQueue.put({"close":None})
    
    class HeartBeatSendingThread(Thread):
        ''' Sends out HeartBeat signals on the wire at the desired frequency '''
        def __init__(self, requestQueue, heartBeatId=0):
            ''' Constructor. '''
            Thread.__init__(self)
            self.requestQueue = requestQueue
            self.heartBeatId  = heartBeatId
            self.heartBeatSequenceId = 0
            self.cmdTrackingId = 0
            self.senderSocket = createBroadcastSender()
            self.bps = -1;
        
        def run(self):
            nextHeartBeatTime = 1.0 
            oldTime = datetime.datetime.now()
            heartBeatTimeout = oldTime + datetime.timedelta(seconds = nextHeartBeatTime)
            while running:
                # block until there's something to do
                timeout = heartBeatTimeout - datetime.datetime.now()
                try:
                    signal = self.requestQueue.get(True, timeout.total_seconds()) # XXX timeout could be negative!! FIXME
                    print signal
                    try:
                        if signal["frequency"] > 0:
                            freq = signal["frequency"]
                            if isinstance(freq, basestring):
                                freq = float(freq)
                            print "Received frequency %d" % freq
                            self.bps = float(freq)/60
                            print "bps is %f" % self.bps
                            nextHeartBeatTime = 1/self.bps
                        else: # invalid frequency, reset to defaults
                            self.bps = -1
                            nextHeartBeatTime = 1.0
                        heartBeatTimeout = oldTime + datetime.timedelta(seconds = nextHeartBeatTime) # XXX be careful about this - it will cause us to skip a beat, which we don't want to do.
                    except AttributeError:
                        pass
                                            
                    currentTime = datetime.datetime.now()
                    if currentTime >= heartBeatTimeout:
                        self.sendHeartBeat()
                        oldTime = currentTime
                        heartBeatTimeout = oldTime + datetime.timedelta(seconds = nextHeartBeatTime)
                
                except Queue.Empty:
                    if self.bps > 0:
                        self.sendHeartBeat()
                    oldTime = datetime.datetime.now()
                    heartBeatTimeout = oldTime + datetime.timedelta(seconds = nextHeartBeatTime)
                    
            self.senderSocket.close()
                    
                    
        def sendHeartBeat(self):
            print "Sending heart beat"
            heartBeatData = struct.pack("=BBHLfL", self.heartBeatId, self.heartBeatSequenceId, 1000/self.bps, 10, self.bps*60, time.time())
            self.heartBeatSequenceId += 1
            if (self.heartBeatSequenceId >= 256) :
                self.heartBeatSequenceId = 0
            self.senderSocket.sendto(heartBeatData, (BROADCAST_ADDR, HEARTBEAT_PORT)) # haz exception XXX?

# XXX utility function
def createBroadcastSender(ttl=MULTICAST_TTL):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    return sock
    
def createBroadcastListener(port, addr=BROADCAST_ADDR):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Set some options to make it multicast-friendly
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass # Some systems don't support SO_REUSEPORT

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    sock.bind(('', port))
        
    return sock

        
class CommandSender():
    ''' Sends out commands on the wire '''
    def __init__(self):
        ''' Constructor. '''
        self.senderSocket = createBroadcastSender()

    def sendCommand(self, unitId, command, data):
        commandData = struct.pack("=BBHL", unitId, self.cmdTrackingId, command_id, data) # XXX for the moment, no extra data associated with command  XXX WTF IS THE COMMAND???
        self.cmdTrackingId += 1
        if (self.cmdTrackingId >= 256):
            self.cmdTrackingId = 0
        self.senderSocket.sendto(commandData, (BROADCAST_ADDR, COMMAND_PORT))
                
            
            
def handleCommandData(commandData):
    receiverId, commandTrackingId, commandId, data = struct.unpack("=BBHL", commandData)
    print "received command"
    print "receiverId is ", receiverId
    print "command is", commandId
    print "data is", data
    if receiverId is gReceiverId  or receiverId is ALL_LISTENERS: # it's for us!
        if commandId is Commands.STOP_ALL:
            pass # should stop synthetic heartbeat
        elif commandId is Commands.STOP_HEARTBEAT:
            pass # should stop synthetic heartbeat
        elif commandId is Commands.START_HEARTBEAT:
            print "Received heartbeat start command, frequency", data
            try:
                heartBeatSender.setHeartBeatFrequency(int(data))
            except ValueError:
                print "Heartbeat frequency non-integer"
            
def main():
    global running
    global heartBeatSender
    running = True
    
    heartBeatSender = HeartBeatSender()
    commandListener = createBroadcastListener(COMMAND_PORT)
    heartBeatSender.setHeartBeatFrequency(60)
    
    try:
        while (running):
            readfds = [commandListener]
            inputReady, outputReady, exceptReady = select(readfds, [], [])
            if inputReady:
                for fd in inputReady:
                    if fd is commandListener:
                        commandData = fd.recv(1024)
                    handleCommandData(commandData)

    except KeyboardInterrupt: # need something besides a keyboard interrupt to stop? or not?XXX
        print "Keyboard interrupt detected, terminating"

    running = False
    commandListener.close()

        

if __name__ == '__main__':
    main()
    
