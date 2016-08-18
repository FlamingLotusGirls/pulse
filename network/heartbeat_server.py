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

#BROADCAST_ADDR = "224.51.105.104"
BROADCAST_ADDR = "255.255.255.255"
HEARTBEAT_PORT = 5000
COMMAND_PORT   = 5001
MULTICAST_TTL  = 4

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
    
    class HeartBeatSendingThread(Thread):
        ''' Sends out HeartBeat signals on the wire at the desired frequency '''
        def __init__(self, requestQueue, heartBeatId=0):
            ''' Constructor. '''
            Thread.__init__(self)
            self.requestQueue = requestQueue
            self.heartBeatId  = heartBeatId
            self.heartBeatSequenceId = 0
            self.cmdTrackingId = 0
            self.socket = createBroadcastSender()
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
                            self.bps = freq/60
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
                    
                    
        def sendHeartBeat(self):
            print "Sending heart beat"
            heartBeatData = struct.pack("=BBHLfL", self.heartBeatId, self.heartBeatSequenceId, 1000/self.bps, 10, self.bps*60, time.time())
            self.heartBeatSequenceId += 1
            if (self.heartBeatSequenceId >= 256) :
                self.heartBeatSequenceId = 0
            self.socket.sendto(heartBeatData, (BROADCAST_ADDR, HEARTBEAT_PORT)) # haz exception XXX?

# XXX utility function
def createBroadcastSender(ttl=MULTICAST_TTL):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
#    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    return sock
        
class CommandSender():
    ''' Sends out commands on the wire '''
    def __init__(self):
        ''' Constructor. '''
        self.socket = createBroadcastSender()

    def sendCommand(self, unitId, command, data):
        commandData = struct.pack("=BBHL", unitId, self.cmdTrackingId, command_id, data) # XXX for the moment, no extra data associated with command  XXX WTF IS THE COMMAND???
        self.cmdTrackingId += 1
        if (self.cmdTrackingId >= 256):
            self.cmdTrackingId = 0
        self.socket.sendto(commandData, (BROADCAST_ADDR, COMMAND_PORT))
        
        
class HeartBeatHttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith(".png"):
                f=open("." + self.path, "rb")
                self.send_response(200)
                self.send_header('Content-type','image/png')
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                return
        elif self.path.endswith(".gif"):
                f=open("." + self.path, "rb")
                self.send_response(200)
                self.send_header('Content-type','image/gif')
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                return
        elif self.path.endswith(".jpeg"):
                f=open("." + self.path, "rb")
                self.send_response(200)
                self.send_header('Content-type','image/jpeg')
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                return
        elif self.path.endswith(".html"):
                f=open("." + self.path, "rb")
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                return
        elif self.path.endswith(".js"):
                f=open("." + self.path, "rb")
                self.send_response(200)
                self.send_header('Content-type','application/javascript')
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                return
        else:
            self.send_response(404)
            self.send_header('Content-type','text/html')
            self.end_headers()
#            self.wfile.write(get())
            return
        
    def do_POST(self):        
        ctype, pdict = parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            postvars = parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = parse_qs(
                    self.rfile.read(length), 
                    keep_blank_values=1)
        else:
            postvars = {}
        if self.path == "/heartBeatFrequency":
            frequency = postvars["frequency"][0]
            print frequency
            if not frequency:
                return
            heartBeatSender.setHeartBeatFrequency(frequency)
            self.send_response(200)
        elif self.path == "/command":
            command = postvars["command"][0]
            receiverId = postvars["receiverId"][0]
            data       = postvars["cmdData"][0]
            commandSender.sendCommand(command, receiverId, data)
            self.send_response(200)
        else:
            self.send_response(404)
        

if __name__ == '__main__':
    running = True
    PORT = 8666
    
    heartBeatSender = HeartBeatSender()
    commandSender   = CommandSender()
    httpd = BaseHTTPServer.HTTPServer(("localhost", PORT), HeartBeatHttpHandler)
    time.sleep(5)
    heartBeatSender.setHeartBeatFrequency(60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "Keyboard interrupt detected, terminating"
        running = False
    httpd.server_close()
