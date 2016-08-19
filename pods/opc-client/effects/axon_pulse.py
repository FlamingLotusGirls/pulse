import math
import random
import numpy

from effectlayer import *
from operator import itemgetter

def myIdxgetter(axon):
    return int(axon[0][1:-1])


class AxonPulseLayer(EffectLayer):
    '''
    Creates a pulse through the axon, from one dendrite to the other.
    Direction --  1 : lower to upper, -1: upper to lower
    Note that this effect is *not* self contained - it requires someone 
    else to start the pulse.
    '''

    def __init__(self):
        self.pulsing = False
        self.timeStart = 0
        self.velocity = 20 # indices per second to traverse
        #self.pulseHeight = [0.9, 1.0, 0.8, 0.6, 0.3, 0.2]
        self.pulseHeight = [0.05, 0.05, 0.05, 0.05, 0.1, 0.15, 0.2, 0.3, 0.6, 0.8, 1.0, 0.9]
        self.direction = 1
        self.needSetup = True
        self.startIdx = 0
        self.maxi = 0;
        self.maxj = 0;
        self.maxframeIdx = 0;
        self.orderedAxonList = []
    
    def startPulse(self, direction=1):
        self.pulsing = True
        self.timeStart = time.time()
        if direction != self.direction:
            self.direction = 1 if direction == 1 else -1
            self.orderedAxonList.reverse()
            print "CSW - reversing list!!\r"
#        print "!!!!!!!!!!!!!!!!!!!START PULSE!!!!!!!!!!!!!\r"
        
    def isPulsing(self):
        return self.pulsing
        
        
    def doSetup(self, model):
        # create an ordered list of the axon indices
        # get axon indices
        # get names of axon indices - map [name, idx]
        # order names of axon indices - ordered map [name, idx]
        # create tuple of idx's associated with the same axon segment
        # add tuple to new list of tuples.
        axonList = [[model.pointNames[idx],idx] for idx in model.axonIndices ]
#        axonList.sort(key=itemgetter(0))
        axonList.sort(key=myIdxgetter)
        self.orderedAxonList = []
        lastPoint = None
        tempTuple = []
        i = 0
        for axonPoint in axonList:
            print axonPoint[0] + "\r"
            i += 1
            # I'm comparing the names - we're looking for everything but the last character. 
            if not lastPoint or axonPoint[0].startswith(lastPoint[0][:-1]):
                tempTuple.append(axonPoint)
            else: # no match
                self.orderedAxonList.append(tempTuple)
                tempTuple = []
            lastPoint = axonPoint
        self.orderedAxonList.append(tempTuple)
        
        if self.direction < 0:
            reversed(self.orderedAxonList) 
            
        print "\r"
        for axon in self.orderedAxonList:
            print "axon is " + axon[0][0] + "\r"
       # print "first axon is " + self.orderedAxonList[0][0][0] + "\r"
       # print "last axon is " + self.orderedAxonList[-1][0][0] + "\r"
        
        self.needSetup = False
 
    def render(self, model, params, frame):
        # immediate bail if we're not pulsing
        if not self.pulsing:
            return
            
        # okay. What do I need? I need the axon indices, and I need to know how
        # many of them there are. And I need their names. 
        if self.needSetup :
            self.doSetup(model)
        # check time, move pulse down the axon
        timeExpired = time.time() - self.timeStart
        leadingEdgeIdx = self.startIdx + int(math.floor((self.velocity * timeExpired)))
        trailingEdgeIdx = leadingEdgeIdx - (len(self.pulseHeight)) + 1
#        print "leading edge idx is " + str(leadingEdgeIdx) + "\r"
        
        # can I count backward in python ranges? It's probably a bad idea...
        havePulse = False
        for i in range(trailingEdgeIdx, leadingEdgeIdx+1): 
            if i < 0 or i > len(self.orderedAxonList)-1:
                continue
            for j in range(0,len(self.orderedAxonList[i])):
#                if i > self.maxi:
#                    self.maxi = i
#                if j > self.maxj:
#                    self.maxj = j
#                if self.orderedAxonList[i][j][1] > self.maxframeIdx:
#                    self.maxframeIdx = self.orderedAxonList[i][j][1]
#                print "id i is " + str(self.maxi) + "\r"
#                print "id j is" + str(self.maxj) + "\r"
#                print "idx in frame is " + str(self.maxframeIdx) + "\n\r"
                frame[self.orderedAxonList[i][j][1]] = self.pulseHeight[i-trailingEdgeIdx]
            havePulse = True
            
        self.pulsing = havePulse
    
                
            