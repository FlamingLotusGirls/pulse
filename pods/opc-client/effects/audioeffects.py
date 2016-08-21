# PyAudio - get volume off of the microphone.
# We'll figure out what to do with it later... 
# This is the equivalent to recordTest.py with the alsadriver, only with pyAudio so I can
# run it on the mac.  

import pyaudio
import sys
import struct
import math
from threading import Thread
from threading import Lock
import threading
from effectlayer import *


def get_rms( block ):
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )

FORMAT = pyaudio.paInt16 
CHANNELS = 2
RATE = 44100  
INPUT_BLOCK_TIME = 0.05
#INPUT_BLOCK_TIME = 0.5
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)
SHORT_NORMALIZE = (1.0/32768.0)

# open the sucker...
#p = pyaudio.PyAudio()
#print pyaudio.get_portaudio_version()
#print pyaudio.get_portaudio_version_text()
#print p.get_device_count()
#print p.get_default_input_device_info()
#print p.get_host_api_count()
#print p. get_host_api_info_by_index(0)
#print p.get_device_info_by_index(0)['name']
#print p.get_device_info_by_index(1)['name']
#print p.get_device_info_by_index(2)['name']

#device_index = 0 # built in microphone, not default device

#stream = p.open(format = FORMAT,
#                channels = CHANNELS,
#                rate = RATE,
#                input = True,
#                input_device_index = device_index,
#                frames_per_buffer = INPUT_FRAMES_PER_BLOCK)
                

# now let's read some frames!!!
#try:
#    for idx in range(0,60):
#        block = stream.read(INPUT_FRAMES_PER_BLOCK)
#        rms = get_rms(block)
#        print rms
#except IOError, e:
#    print( "Error recording: %s"%(e) )
    
# this is a filter based on a 10 bit, rather than 16 bit, sample
DCFILTER = 5
BASSFILTER = 3

TRIG1_STEP   =1
TRIG1_CLAMP  =70
BRIGHT1_UP   =(65535 / 30)
BRIGHT1_DOWN =(65535 / 300)
BRIGHT1_MAX  =64
 
TRIG2_STEP   =1
TRIG2_CLAMP  =40
BRIGHT2_UP   =(65535 / 40)
BRIGHT2_DOWN =(65535 / 700)
BRIGHT2_MAX  =64



class AudioEffectLayer(EffectLayer):
    
    rms = 0
    rms_lock = threading.Lock()
    device_index = 0
    running = True
    tickcount = 0
    accumDC   = 0
    accumN    = 0
    accumBass = 0
    tmax1     = 0
    tmax2     = 0
    ibright1  = 0
    ibright2  = 0
    brightaccum1 = 0
    brightaccum2 = 0
    maxbright = 0
    
    samplemultiplier = 20 # converting between 4KHz mono and 44KHz stereo...

    def __init__(self):
        myThread = Thread(target=self.runAudio)
#        myThread = Thread(target=self.blipAudio)
        myThread.daemon = True
        myThread.start()
#        runAudio()

    def render(self, model, params, frame):
        localRms = self.lockAndGetRms()
        localRms = (localRms*5) if localRms < 0.1 else 1.0
        frame[:] = localRms
        print localRms
        #frame[:] = 1.0

    def runAudio(self):
        print ("attempting to run audio");
        p = pyaudio.PyAudio()
        stream = p.open(format = FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    input = True,
                    input_device_index = self.device_index,
                    frames_per_buffer = INPUT_FRAMES_PER_BLOCK)
        while self.running:
            try:
                block = stream.read(INPUT_FRAMES_PER_BLOCK)
                newRms = get_rms(block)
                self.lockAndSetRms(newRms);
            except IOError, e:
                print( "Error recording: %s"%(e) )
        
    def lockAndSetRms(self, new_rms):
        self.rms_lock.acquire()
        self.rms = new_rms
        self.rms_lock.release()
    
    def lockAndGetRms(self):
        self.rms_lock.acquire()
        newRMS = self.rms
        self.rms_lock.release()
        return newRMS
        
    def kill(self):
        self.running = False
        myThread.join()
            
# Adapted  from Austin Appleby, Bliplace project
# We note that this is based on a 10-bit sample, rather than the 16-bit samples that we have
# And we also note that they're sampling at 4KHz, and we're sampling at 44KHz. And they're 
# probably sampling mono, whereas we're sampling stereo.
# May work anyway, though.
# and it may or may not have been signed in the original...


    def processSample(self, sample) :
        # remove rumble + residual DC bias
        sample = sample - self.accumDC
        self.accumDC = self.accumDC + (sample >> DCFILTER) # this seems to imply that sample is signed. ibright is uint16
        
        # de-noise sample
        self.accumN = (self.accumN + sample) >> 1
        sample = self.accumN
 
        # split into bass & treble        
        sample = sample - self.accumBass
        self.accumBass = self.accumBass + (sample >> BASSFILTER)
        
        bass = self.accumBass
        treble = sample
        
        # Every 64 * samplemultiplier samples, adapt triggers to volume
        self.tickcount = self.tickcount + 1 if self.tickcount < ((64*self.samplemultiplier)-1) else 0       
        if (self.tickcount == 0):
            if self.brightaccum1 > BRIGHT1_MAX*64*self.samplemultiplier:  # too bright. move trigger up if not at max
                if self.tmax1 < 32000:
                    self.tmax1 = self.tmax1 + TRIG1_STEP
                    self.tmax1 = self.tmax1 + (self.tmax1 >> 10)
            else:                                   # move trigger down if not at min
                if self.tmax1 > TRIG1_CLAMP:
                    self.tmax1 = self.tmax1 - (self.tmax1 >> 10)
                    self.tmax1 = self.tmax1 - TRIG1_STEP

            if self.brightaccum2 > BRIGHT2_MAX*64*self.samplemultiplier:
                if self.tmax2 < 32000:
                    self.tmax2 = self.tmax2 + TRIG2_STEP
                    self.tmax2 = self.tmax2 + (self.tmax2 >> 10)
            else:
                if self.tmax2 > TRIG2_CLAMP:
                    self.tmax2 = self.tmax2 - (self.tmax2 >> 10)
                    self.tmax2 = self.tmax2 - TRIG2_STEP
            
            self.brightaccum1 = 0
            self.brightaccum2 = 0
                    

        # Ramp our brightness up if we hit a trigger, down otherwise
        # note that ibright is an uint16 integer brightness
        if (bass > self.tmax2):
            if (self.ibright2 <= (65535-BRIGHT2_UP)):  ## another assumption of 16 bits!
                self.ibright2 = self.ibright2 + BRIGHT2_UP
        else:
            if (self.ibright2 >= BRIGHT2_DOWN):
                self.ibright2 = self.ibright2 - BRIGHT2_DOWN
 
        if (treble > self.tmax1):
            if (self.ibright1 <= (65535-BRIGHT1_UP)): ## and another
                self.ibright1 = self.ibright1 + BRIGHT1_UP
        else:
            if (self.ibright1 >= BRIGHT1_DOWN):
                self.ibright1 = self.ibright1 - BRIGHT1_DOWN
                
        # accumulate brightness...
        self.brightaccum1 = self.brightaccum1 + (self.ibright1 >> 8)
        self.brightaccum2 = self.brightaccum2 + (self.ibright2 >> 8)
        
        if (self.brightaccum1 > self.maxbright) :
            self.maxbright = self.brightaccum1
            
        if self.brightaccum1 > 0:
        #    print "bright"
        #    print self.brightaccum1
        #    print self.maxbright
            pass
                
                
    def blipAudio(self):
        # process sample
        # read block
        # for each sample, do update...
        print ("attempting to run weird audio");
        p = pyaudio.PyAudio()
        stream = p.open(format = FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    input = True,
                    input_device_index = self.device_index,
                    frames_per_buffer = INPUT_FRAMES_PER_BLOCK)
        while self.running:
            try:
                block = stream.read(INPUT_FRAMES_PER_BLOCK)
                # we will get one short out for each 
                # two chars in the string.
                count = len(block)/2
                format = "%dh"%(count)
                shorts = struct.unpack( format, block )

                # iterate over the block.
                sum_squares = 0.0
                for sample in shorts:
                    self.processSample(sample)
#                newRms = float(self.brightaccum1)/65535
                newRms = float(self.ibright1)/65535
                print self.brightaccum1
                print newRms
                self.lockAndSetRms(newRms);
            except IOError, e:
                print( "Error recording: %s"%(e) )
    	#Update()
 
		#uint8_t bright1 = pgm_read_byte(exptab+(ibright1 >> 8));
		#uint8_t bright2 = pgm_read_byte(exptab+(ibright2 >> 8));
 
		#brightaccum1 += pgm_read_byte(gammatab+bright1);
		#brightaccum2 += pgm_read_byte(gammatab+bright2);
 
		#setbright(bright1,bright2,bright1);
                

    

