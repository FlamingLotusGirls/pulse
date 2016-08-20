import math
import random
import numpy
import time

from effectlayer import *
from axon_pulse import *

class MorseLayer2(EffectLayer):

    def __init__(self, lowerStringsArray, upperStringsArray = None):
        self.upperStrings = upperStringsArray
        self.lowerStrings = lowerStringsArray
        self.LEDs = []
        self.pulse = AxonPulseLayer()
        self.prevPulseState = 0 # not pulsing
        self.stringIdx = 0
        if (self.upperStrings == None) :
            self.upperStrings = self.lowerStrings

    def render(self, model, params, frame):
        curNumLEDs = frame.size/3
        if (curNumLEDs != len(self.LEDs)) :
            print ("render - Setup LEDs\r")
            self.LEDs = []
            for idx in range(curNumLEDs):
                if idx in model.lowerIndices:
                    LED = MorseLED(self.lowerStrings[self.stringIdx % len(self.lowerStrings)], True, "Lower")
                elif idx in model.upperIndices:
                    LED = MorseLED(self.upperStrings[self.stringIdx % len(self.upperStrings)], True, "Upper") 
                else:
                    LED = MorseLED(" ", False)
                self.LEDs.append(LED)        
        
        for idx in range(len(self.LEDs)) : 
            if len(frame) > idx and (not idx in model.axonIndices): # only Morse the dendrites...
                frame[idx] = self.LEDs[idx].render(params)
        
        # start an axon pulse if a button is down and we're not
        # currently pulsing
        if not self.pulse.isPulsing():
            # if we just finished our pulse, change up the strings
            if self.prevPulseState != 0:
                self.stringIdx = self.stringIdx + 1
                print "switching up strings!\r"
                print "lower string is " + self.lowerStrings[self.stringIdx % len(self.lowerStrings)] + "\r"
                print "upper string is " + self.upperStrings[self.stringIdx % len(self.upperStrings)] + "\r"
                for LED in self.LEDs:
                    if LED.userData == "Upper":
                        LED.initString(self.upperStrings[self.stringIdx % len(self.upperStrings)], True)
                    elif LED.userData == "Lower":
                        LED.initString(self.lowerStrings[self.stringIdx % len(self.lowerStrings)], True)
                self.prevPulseState = 0
            
            if params.buttonState[0]:
                print "start pulse forward\r"
                self.pulse.startPulse(1)
                self.prevPulseState = 1
            elif params.buttonState[1]:
                print "start pulse backward\r"
                self.pulse.startPulse(-1)
                self.prevPulseState = 1
        else:
            self.pulse.render(model, params, frame)
            
            

            
        # okay - so what should be happening? A slow pulse with some variation on one side, becomes coherent
        # and then goes to the morse message that then moves over to the other side?
        
# Basic morse characteristics
class Morse:
    UNIT = 300
    INTER_LETTER_TIME = UNIT*3
    SPACE_TIME = UNIT*7
    INTERSTITIAL_TIME = UNIT
    DOT_TIME = UNIT
    DASH_TIME = UNIT*3
    REFRESH_TIME = UNIT*9
    DOT = 0
    DASH = 1

    mapping =  {'a':[0,1], 
                'b':[1,0,0,0],
                'c':[1,0,1,0],
                'd':[1,0,0],
                'e':[0],
                'f':[0,0,1,0],
                'g':[1,1,0],
                'h':[0,0,0,0],
                'i':[0,0],
                'j':[0,1,1,1],
                'k':[1,0,1],
                'l':[0,1,0,0],
                'm':[1,1],
                'n':[1,0],
                'o':[1,1,1],
                'p':[0,1,1,0],
                'q':[1,1,0,1],
                'r':[0,1,0],
                's':[0,0,0],
                't':[1],
                'u':[0,0,1],
                'v':[0,0,0,1],
                'w':[0,1,1],
                'x':[1,0,0,1],
                'y':[1,0,1,1],
                'z':[1,1,0,0],
                'A':[0,1], 
                'B':[1,0,0,0],
                'C':[1,0,1,0],
                'D':[1,0,0],
                'E':[0],
                'F':[0,0,1,0],
                'G':[1,1,0],
                'H':[0,0,0,0],
                'I':[0,0],
                'J':[0,1,1,1],
                'K':[1,0,1],
                'L':[0,1,0,0],
                'M':[1,1],
                'N':[1,0],
                'O':[1,1,1],
                'P':[0,1,1,0],
                'Q':[1,1,0,1],
                'R':[0,1,0],
                'S':[0,0,0],
                'T':[1],
                'U':[0,0,1],
                'V':[0,0,0,1],
                'W':[0,1,1],
                'X':[1,0,0,1],
                'Y':[1,0,1,1],
                'Z':[1,1,0,0],
                '1':[0,1,1,1,1],
                '2':[0,0,1,1,1],
                '3':[0,0,0,1,1],
                '4':[0,0,0,0,1],
                '5':[0,0,0,0,0],
                '6':[1,0,0,0,0],
                '7':[1,1,0,0,0],
                '8':[1,1,1,0,0],
                '9':[1,1,1,1,0],
                '0':[0,0,0,0,0]}
              
# Class for LEDS
# Morse timing:  ON: DOT_TIME, DASH_TIME
#                OFF: INTERSTITIAL_TIME, INTRA_LETTER_TIME, SPACE_TIME, REFRESH_TIME
# Pointers into string - major_index -> pointer to char in string
#                      - minor_index -> pointer to dot/dash in char, if appropriate
# The pointers are pre-incremented, that is, we increment the pointers *before* we hit
# the target time, not before
class MorseLED():
    def __init__(self, theString, randomize = False, userData = None):
        self.userData = userData # can be used for identifying the LED
        self.initString(theString, randomize)
    
    def initString(self, theString, randomize):
        self.string = theString
        if randomize == False: 
            self.target_time = 0
            self.major_index = 0  # start at the beginning
            self.minor_index = 0  # the index in the morse dot-dash series
            self.mode = 0 # 0 is off, 1 is on...
            self.iteration = 0
        else:
            # randomly set our position in the string.
            totalTime = self.calculateMorseStringTime(theString)
            currentTimeOffset = random.randrange(0,totalTime)
            self.target_time, self.major_index, self.minor_index, self.mode = self.calculateMorseParams(theString, currentTimeOffset)
        

    # calculate the total amount of time it takes to display this string
    def calculateMorseStringTime(self, theString):
        morseTime = 0
        for char in theString:
            morseTime += self.calculateMorseCharTime(char)
        morseTime += Morse.REFRESH_TIME
        return morseTime
    
    # calculate the total amount of time it takes to display this character (plus the intra_letter_time)
    # this is not *quite* the same as the calculation done in the render code, but should
    # be fine for most cases (and no one will notice the cases in which it is not)
    def calculateMorseCharTime(self, theChar):
        morseTime = 0
        if not theChar in Morse.mapping:
            morseTime += Morse.SPACE_TIME
        else:
            dotDashList = Morse.mapping[theChar]
            for dotDash in dotDashList:
                if dotDash == Morse.DOT:
                    morseTime += Morse.DOT_TIME
                elif dotDash == Morse.DASH:
                    morseTime += Morse.DASH_TIME
            
            morseTime += (len(dotDashList) - 1) * Morse.INTERSTITIAL_TIME
            morseTime += Morse.INTER_LETTER_TIME
        return morseTime
        
    # For a given time offset, calculate the params determine where we are in the string
    # need major index, minor index, on/off, target time
    def calculateMorseParams(self, theString, currentTimeOffset):
        prevTimeEnd = 0
        curTimeEnd = 0
        
        # Find the index of the char that we're displaying (this is the major index in the
        # morse parameters)
        for charIdx in range(len(theString)):
            theChar = theString[charIdx]
            curTimeEnd += self.calculateMorseCharTime(theChar)
            if curTimeEnd > currentTimeOffset:
                break
            if charIdx < len(theString) - 1:  # only resetPrevTime if there's another character
                prevTimeEnd = curTimeEnd   
        major_index = charIdx
        curTimeEnd = prevTimeEnd
        
        # Find the dot or dash in the index that we're displaying (this is the minor index in 
        # the morse parameters)
        isPrintable = theChar in Morse.mapping
        if isPrintable:
            dotDashList = Morse.mapping[theString[charIdx]]
            for dotDashIdx in range(len(dotDashList)):
                dotDash = dotDashList[dotDashIdx]
                if dotDash == Morse.DOT:
                    curTimeEnd += Morse.DOT_TIME
                else:
                    curTimeEnd += Morse.DASH_TIME
                if dotDashIdx < len(dotDashList) - 1:
                    curTimeEnd += Morse.INTERSTITIAL_TIME                
                if curTimeEnd > currentTimeOffset:
                    break
                if dotDashIdx < len(dotDashList) - 1: # only resetPrevTime if there's another dot/dash
                    prevTimeEnd = curTimeEnd
            minor_index = dotDashIdx
            if dotDash == Morse.DOT and prevTimeEnd + Morse.DOT_TIME > currentTimeOffset:
                onOff = 1
                targetTime = prevTimeEnd + Morse.DOT_TIME - currentTimeOffset
            elif dotDash == Morse.DASH and prevTimeEnd + Morse.DASH_TIME > currentTimeOffset:
                onOff = 1
                targetTime = prevTimeEnd + Morse.DASH_TIME - currentTimeOffset
            else:
                onOff = 0
                # in the middle of dotdash sequence?
                if dotDashIdx < len(dotDashList) - 1:
                    if dotDash == Morse.DOT:
                        targetTime = prevTimeEnd + Morse.DOT_TIME + Morse.INTERSTITIAL_TIME - currentTimeOffset
                    else:
                        targetTime = prevTimeEnd + Morse.DASH_TIME + Morse.INTERSTITIAL_TIME - currentTimeOffset
                else: # end of dot dash sequence. Either in between letters or in reset                       
                    # end of String? 
                    if charIdx < len(theString) - 1:
                        targetTime = prevTimeEnd + Morse.INTER_LETTER_TIME - currentTimeOffset
                    else:
                        targetTime = prevTimeEnd + Morse.REFRESH_TIME - currentTimeOffset 
                
        else: # not printable - a space # also check for reset time!
            onOff = False
            targetTime = curTimeEnd + Morse.SPACE_TIME #XXX what about reset time?
            minor_index = 0
            
        # okay. are the indices the current value, or the next value? not that it really matters, but...
        if targetTime < 0:
            targetTime = 0
        
        return int(time.time()*1000) + targetTime, major_index, minor_index, onOff
                   
        
    def render(self, params):
        # check whether we should restart the pattern - more than a second has passed since
        # the last time we've rendered. XXX TODO
        # look at current time... decide if we need to do the next item...
        current_time = int(time.time() *1000)
        #print "target", self.target_time
        #print current_time
        if current_time >= self.target_time:
            if self.mode == 0: # if we're currently off, turn on XXX - we start off, but we haven't called get next printable at that point.
                if self.major_index == -1:
                    # invalid string. Blink.
                    self.target_time = current_time + self.INTERSTITIAL_TIME
                else:
                    letter = self.string[self.major_index]
                
                    if letter in Morse.mapping: # valid letter
                        #print "minor index is ", self.minor_index
                        dotdash = Morse.mapping[letter][self.minor_index] # get current dot-dash
                        if dotdash == 0:  # dot!
                            self.target_time = current_time + Morse.DOT_TIME
                        else: # dash!
                            self.target_time = current_time + Morse.DASH_TIME
                    else: # invalid string. Simply blink
                        self.target_time = current_time + Morse.INTERSTITIAL_TIME
                
                self.mode = 1 # we're now on
                    
            else: # if we're currently on, turn off
                self.mode = 0
                dark_time = 0
                next_printable = self.getNextPrintable()
                # check - are there no printable characters?
                if next_printable == -1:
                    dark_time = Morse.INTERSTITIAL_TIME
                # have we gone past the end of the string?
                elif next_printable < self.major_index:
                    dark_time = Morse.REFRESH_TIME
#                    self.iteration += 1
#                    print "iteration is", self.iteration
                # have we moved past some non-printables?
                elif next_printable > self.major_index + 1:
                    dark_time = Morse.SPACE_TIME
                # going to the next letter
                elif next_printable == self.major_index + 1:
                    dark_time = Morse.INTER_LETTER_TIME
                # still in the middle of the letter
                else:
                    dark_time = Morse.INTERSTITIAL_TIME
                
                # update pointers...
                if next_printable != self.major_index:
                    self.major_index = next_printable
                    self.minor_index = 0
                else:
                    self.minor_index = self.minor_index + 1
                
                self.target_time = current_time + dark_time
                
        return self.mode
        
    def getNextPrintable(self):
        cur_char = self.string[self.major_index]
        # if we're in the middle of a letter, the next printable is the current letter
        # print "cur char is ", cur_char
        # print "minor index is ", self.minor_index
        # print "mapping length is ", len(Morse.mapping[cur_char])
        if cur_char in Morse.mapping and self.minor_index+1 < len(Morse.mapping[cur_char]):
            return self.major_index
        
        # other wise - figure out where the next printable character is
        start_idx = self.major_index
        str_len = len(self.string)
        for i in range(str_len):
            cur_idx = (i + 1 + start_idx) % str_len
            cur_char = self.string[cur_idx]
            if cur_char in Morse.mapping:
                break
        if i==str_len:
            return -1
        else:
            return (i + 1 + start_idx) % str_len
'''            
class axonDashEffect:

    def __init__(directionVector): # may also have pulseWidth
        if directionVector > 10:
            diretionVector = 10
        elif directionVector < -10:
            directionVector = -10
        
        self.directionVector = directionVector
    
    def start:
        self.pulseLocation = 0
        self.time = 0
        self.effectOn = True
        self.play = True
        self.lastRenderTime = time.time() # *1000?
        
    def pause:
        self.play = False
    
    def unpause:
        self.play = True
        
    def stop:
        self.effectOn = False
        self.play = False
    
    
    def render(model, frame):
        # move the pulse location 
        renderTime = time.time()
        deltaTime = renderTime - self.lastRenderTime
        pulseLocation += pulseLocation * directionVector  # watch out on the negatives
        self.lastRenderTime = renderTime

        axonIndices = model.getAxonIndices()
        axons = []
        for idx in axonIndices:
            axons.append((idx, model.pointNames[idx]))   
        axonsSorted = sorted(axons, key = itemgetter(1)) # if direction is negative, sort the other way! XXX
        
        numberBuckets = len(axonsStorted)/3
        
        # trailing edge is 3 buckets. Leading edge is 1 bucket. We start at position
        # -1
        # have to think about this for a moment
        
        # and now move the pulse location by our velocity depending on the time taken

        # group by threes
        # now send pulse
        # 
        
        # if the entire pulse was outside of the axon, stop the animation
        if pulseOver:
            self.stop()
'''
     