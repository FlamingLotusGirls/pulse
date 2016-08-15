# Various heartbeat options

import datetime
import os
# from operator import itemgetter, attrgetter
# from select import select
import serial
import socket
import struct
import sys
import pysimpledmx
import time

DMX_RED_CHANNEL = 2
DMX_GREEN_CHANNEL = 3
DMX_BLUE_CHANNEL = 4
DMX_WHITE_CHANNEL = 5
DMX_CHANNEL_COUNT = 6 # Can be 6/7/8/12


def heartbeat1(dmx):
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
    print "difference1 = ", (datetime.datetime.now() - now)

def heartbeat2(dmx):
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


def heartbeat1_split(dmx):
    print "heartbeat 1 split"
    # now = datetime.datetime.now()
    # dmx.setChannel(DMX_RED_CHANNEL, 100)
    # dmx.setChannel(DMX_GREEN_CHANNEL+12, 200)
    # dmx.render()
    # time.sleep(0.2)
    # for i in range(20):
    #     dmx.setChannel(DMX_RED_CHANNEL, 100 - i)
    #     dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100-i)
    #     dmx.render()
    #     time.sleep(0.001)
    # dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100)
    # for i in range(85):
    #     dmx.setChannel(DMX_RED_CHANNEL, 100 + i*2)
    #     dmx.render()
    #     time.sleep(0.002)
    # for i in range(100):
    #     dmx.setChannel(DMX_RED_CHANNEL, 200 - i)
    #     dmx.render()
    #     time.sleep(0.001)
    # for i in range(75):
    #     dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 100 + i*2)
    #     dmx.render()
    #     time.sleep(0.002)
    # for i in range(100):
    #     dmx.setChannel(DMX_RED_CHANNEL + DMX_CHANNEL_COUNT, 200 - i)
    #     dmx.render()
    #     time.sleep(0.001)
    # print "difference1_split = ", (datetime.datetime.now() - now)
