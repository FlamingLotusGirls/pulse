import math
import random
import numpy
from effectlayer import *
from effects.color_palette_library import *
from effects.specklayer import Speck
import random

class ColorPaletteBattleLayer(EffectLayer):

    def __init__(self, model):
        self.paletteLibrary = ColorPaletteLibrary()
        self.initPalette(model)
        self.characteristicTime = 1/5. # average rate of color change for a single LED
        self.waitTimes = numpy.array([random.expovariate(self.characteristicTime) for i in range(model.numLEDs)])
        self.lastFrameTime = None
        self.colorChangesInProgress = {}
        self.buttonDown = [False]*2
        self.axonChaseStartTime = None
        self.axonChaseDuration = 4
        self.specks = []
        self.speckColor =[1,1,1]
        self.doSpecks = False
        self.speckFrameDelay = 10
        self.speckFrameIdx = 0
        self.enableSpecks = False

        # Extract axon point positions in one dimension (they are normalized already)
        self.normalized_x_coords = model.nodes[:,1][range(model.numLEDs)]
        self.winningColor = None


    def initPalette(self, model):
        palette = self.paletteLibrary.getPalette()
        self.buttonColors = [palette[0], palette[-1]]
        self.nonButtonColors = palette[1:-1]
        self.colors = [random.choice(self.nonButtonColors) for i in range(model.numLEDs)]

    def render(self, model, params, frame):
        if self.axonChaseStartTime:
            self.renderAxonChase(model, params)
        else:
            self.renderRestingState(model, params)

        frame[:] = self.colors
        if self.doSpecks:
            self.renderSpecks(model, params, frame)
        return frame

    def renderRestingState(self, model, params):
        if not self.lastFrameTime:
            self.lastFrameTime = params.time
        delta = params.time - self.lastFrameTime
        self.lastFrameTime = params.time

        self.waitTimes -= delta

        timedOut = numpy.where(self.waitTimes < 0)

        for i in range(len(params.buttonState)):
            if(params.buttonState[i] and not self.buttonDown[i]):
                self.buttonDown[i] = True
                self.initiateColorChange(self.buttonColors[i], params.time, model)
                self.initiateColorChange(self.buttonColors[i], params.time, model)
                self.initiateColorChange(self.buttonColors[i], params.time, model)
                self.initiateColorChange(self.buttonColors[i], params.time, model)
                self.initiateColorChange(self.buttonColors[i], params.time, model)
                self.initiateColorChange(self.buttonColors[i], params.time, model)
            if not params.buttonState[i]:
                self.buttonDown[i] = False

        colors_to_remove = []
        for led_index, colorChange in self.colorChangesInProgress.items():
            if colorChange['fadeOut']:
                self.colors[led_index] = self.fadeToColor(self.colors[led_index], [1,1,1], stepSize=0.05)
                if numpy.array_equal(self.colors[led_index], [1,1,1]):
                    colorChange['fadeOut'] = False

            else:
                self.colors[led_index] = self.fadeToColor(self.colors[led_index], colorChange['color'])
                if numpy.array_equal(self.colors[led_index], colorChange['color']):
                    colors_to_remove.append(led_index)
        for led_index in colors_to_remove:
            del self.colorChangesInProgress[led_index]



        for i in timedOut[0]:
            self.colors[i] = random.choice(self.nonButtonColors)
            self.waitTimes[i] = random.expovariate(self.characteristicTime)



    def initiateColorChange(self, color, time, model):
        indices = random.sample(model.lowerIndices, len(model.lowerIndices))
        indexToChange = -1
        for i in range(len(indices)):
            if (self.colors[indices[i]] != color).any():
                if indices[i] not in self.colorChangesInProgress:
                    indexToChange = i
                    break
        if indexToChange > -1:
            print indices[indexToChange]
            self.colorChangesInProgress[indices[indexToChange]] = {'color': color, 'fadeOut': True}
        else:
            self.axonChaseStartTime = time
            self.winningColor = color
            print 'YOU WIN'
            if self.enableSpecks:
                self.doSpecks = True
                self.endSpeckTime = time + 5
                self.speckSpawnEndTime = time + 2

    def renderAxonChase(self, model, params):
        chaseFraction = (params.time-self.axonChaseStartTime)/self.axonChaseDuration
        if chaseFraction > 2:
            self.__init__(model)
            return

        for i in range(model.numLEDs):
            if self.normalized_x_coords[i] > (1-chaseFraction):
                self.colors[i] = self.winningColor

    def renderSpecks(self, model, params, frame):
        # advance state machine if we're done with our specks
        if params.time > self.endSpeckTime:
	    self.doSpecks = False
            self.specks = []
            return
        # spawn more specks if we're within the speck span
        if params.time > self.speckSpawnEndTime:
            if self.speckFrameIdx == 0:
                self.specks.append(Speck(self.speckColor, random.randrange(40)))
            self.speckFrameIdx += 1
            if self.speckFrameIdx >= self.speckFrameDelay:
                self.speckFrameIdx = 0

        # draw our specks!
        deadspecks = []
        for speck in self.specks:
            speck.render(model, params, frame)
            if speck.index > model.numLEDs: # if it's gone through all the indices, it's dead
                deadspecks.append(speck)
           
        for speck in deadspecks:
            self.specks.remove(speck)



    def fadeToColor(self, fromColor, toColor, stepSize=0.02):
        diff = numpy.subtract(toColor, fromColor)
        maxDifference = max(numpy.absolute(diff))
        if maxDifference > stepSize:
            amountToAdd = numpy.multiply(stepSize/maxDifference, diff)
            return numpy.add(fromColor, amountToAdd)
        else:
            return toColor



