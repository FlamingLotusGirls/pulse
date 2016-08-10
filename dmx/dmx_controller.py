# Python for controlling the DMX lights according to UDP packets
# Some of this code was shamelessly stolen from Carolyn Wales

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
DMX_GREEN_CHANNEL = 3
DMX_RED_CHANNEL = 2
DMX_BLUE_CHANNEL = 4

running = True
allowHeartBeats = True
currentHeartBeatSource = 1
ser = None
previousHeartBeatTime = None


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


if __name__ == '__main__':
    print "AAAH"
    running = True
    # mydmx.setChannel(2, 255) # set DMX channel 2 to 128
    dmx = pysimpledmx.DMXConnection(DMX_ADDRESS)
    heartBeatListener = createBroadcastListener(HEARTBEAT_PORT)
    commandListener   = createBroadcastListener(COMMAND_PORT)

    try:

        for i in range(256):
            # dmx.setChannel(1, 0)
            # dmx.setChannel(2, i)
            # dmx.setChannel(3, 256-i)   # set DMX channel 3 to 0
            dmx.setChannel(4, i)
            dmx.render()
            print "rendering"
            time.sleep(0.05)
        dmx.close()
    except KeyboardInterrupt:
        print "CLOSING"
        dmx.close()
        running = False
        heartBeatListener.close()
        commandListener.close()
