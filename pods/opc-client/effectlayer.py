from __future__ import print_function
import numpy
import time
import traceback
import colorsys
import random
from math import *

class EffectParameters(object):
    """Inputs to the individual effect layers. Includes basics like the timestamp of the frame we're
       generating, as well as parameters that may be used to control individual layers in real-time.
       """

    time = 0
    targetFrameRate = 40.0 
    
    buttonCnt = 2
    buttonState = [False]*buttonCnt # true if button is pressed or false if it is not pressed
    buttonTimeSinceStateChange = [0]*buttonCnt #how long since the button last changed state

    def __str__(self):
        return "Time: %d, buttonState: %s buttonTimeSinceChange: %s " % (self.time, self.buttonState, self.buttonTimeSinceStateChange)


class EffectLayer(object):
    """Abstract base class for one layer of an LED light effect. Layers operate on a shared framebuffer,
       adding their own contribution to the buffer and possibly blending or overlaying with data from
       prior layers.

       The 'frame' passed to each render() function is an array of LEDs in the same order as the
       IDs recognized by the 'model' object. Each LED is a 3-element list with the red, green, and
       blue components each as floating point values with a normalized brightness range of [0, 1].
       If a component is beyond this range, it will be clamped during conversion to the hardware
       color format.
       """

    transitionFadeTime = 1.0
    maximum_errors = 5

    def render(self, model, params, frame):
        raise NotImplementedError("Implement render() in your EffectLayer subclass")

    def safely_render(self, model, params, frame):
        if not hasattr(self, 'error_count'):
            self.error_count = 0
        try:
            if self.error_count < EffectLayer.maximum_errors:
                self.render(model, params, frame)
        except Exception as err:
            error_log = open('error.log','a')
            error_log.write(time.asctime(time.gmtime()) + " UTC" + " : ")
            traceback.print_exc(file=error_log)
            print("ERROR:", err, "in", self)
            self.error_count += 1
            if self.error_count >= EffectLayer.maximum_errors:
                print("Disabling", self, "for throwing too many errors")
                
        


########################################################
# Simple model-agnostic EffectLayer implementations and examples
########################################################


class MultiplierLayer(EffectLayer):
    """ Renders two layers in temporary frames, then adds the product of those frames
    to the frame passed into its render method
    """
    def __init__(self, layer1, layer2):
        self.layer1 = layer1
        self.layer2 = layer2

    def render(self, model, params, frame):
        temp1 = numpy.zeros(frame.shape)
        temp2 = numpy.zeros(frame.shape)
        self.layer1.render(model, params, temp1)
        self.layer2.render(model, params, temp2)
        numpy.multiply(temp1, temp2, temp1)
        numpy.add(frame, temp1, frame)

class AverageLayer(EffectLayer):
    """ Renders two layers in temporary frames, then adds the average of those frames
    to the frame passed into its render method
    """
    def __init__(self, layer1, layer2):
        self.layer1 = layer1
        self.layer2 = layer2

    def render(self, model, params, frame):
        temp1 = numpy.zeros(frame.shape)
        temp2 = numpy.zeros(frame.shape)
        self.layer1.render(model, params, temp1)
        self.layer2.render(model, params, temp2)
        numpy.add(temp1, temp2, temp1)
        numpy.divide(temp1, 2.0, temp1)
        numpy.add(frame, temp1, frame)


class BlinkyLayer(EffectLayer):
    """Test our timing accuracy: Just blink everything on and off every other frame."""

    on = False

    def render(self, model, params, frame):
        self.on = not self.on
        frame[:] += self.on


class ColorBlinkyLayer(EffectLayer):
    on = False
    def render(self, model, params, frame):
        self.on = not self.on
        color = numpy.array(colorsys.hsv_to_rgb(random.random(),1,1))
        if self.on:
            frame[:] += color


class SnowstormLayer(EffectLayer):
    transitionFadeTime = 1.0
    def render(self, model, params, frame):
        numpy.add(frame, numpy.random.rand(model.numLEDs, 1), frame)


class WhiteOutLayer(EffectLayer):
    """ Sets everything to white """

    transitionFadeTime = 0.5
    def render(self, model, params, frame):
        frame += numpy.ones(frame.shape)
            

class GammaLayer(EffectLayer):
    """Apply a gamma correction to the brightness, to adjust for the eye's nonlinear sensitivity."""

    def __init__(self, gamma):
        # Build a lookup table
        self.lutX = numpy.arange(0, 1, 0.01)
        self.lutY = numpy.power(self.lutX, gamma)

    def render(self, model, params, frame):
        pass
        #frame[:] = numpy.interp(frame.reshape(-1), self.lutX, self.lutY).reshape(frame.shape)

        
class TriangleWaveLayer(EffectLayer):
    """ Ramp the brightness in a triangle wave """
    brightness = 0
    step = 0.001
    def render(self, model, params, frame):
        if self.brightness >= 1:
            self.step = -0.001
        if self.brightness <= 0:
            self.step = 0.001

        color = numpy.array((1,1,1))
        self.brightness += self.step
        frame[:] = self.brightness * color



# A sine wave in the X direction
class SineWaveLayer(EffectLayer):
    startTime = None

    def __init__(self, period = 1.0, color = (1, 1, 1)):
        self.period = period
        self.color = numpy.array(color)

    def render(self, model, params, frame):
        if not self.startTime:
            self.startTime = params.time

        elapsedTime = (params.time - self.startTime)

        # model.nodes[0] is the X coordinates in [0,1] range
        # elapsedTime / self.period will increment by 1/period every second
        radians = (model.nodes[:,0] + elapsedTime / self.period) * 2 * pi

        cosines = numpy.cos(radians)

        # the frame is Nx3 (R/G/B values for each of the N LEDs).
        # reshape(-1,1) converts cosines from a 1D to an Nx1 2D array so it can be
        # multplied with the color array to yield a Nx3 array
        frame[:] = cosines.reshape(-1,1) * self.color


class TestPatternLayer(EffectLayer):
    def __init__(self):
        self.startTime = None

    def render(self, model, params, frame):
        if not self.startTime:
            self.startTime = params.time

        elapsedTime = (params.time - self.startTime)

        cosine = numpy.cos(elapsedTime * 2 * pi);

        frame[:] = cosine * numpy.array([1,0,0])

        
class SpecialEffectsLayer(EffectLayer):
    """ Should be the base class of all special effects layers. These layers
    are temporarily added into the playlist, and are expected to return True to is_done
    when they are finished. Special effects layers should be limited in duration."""
    def __init__(self):
        self.finished = True
    def is_done(self):
        return self.finished



# step through the LEDs in order of frame index
class AddressTestLayer(EffectLayer):
    def __init__(self):
        self.index = 0
        self.switchInterval = 0.5
        self.lastSwitchTime = None
        self.color = numpy.array([1,0,0])
        self.first = 0
        self.last  = 0

    def render(self, model, params, frame):
        if not self.last:
            self.last = model.numLEDs

        if not self.lastSwitchTime:
            self.lastSwitchTime = params.time
        elif params.time - self.lastSwitchTime > self.switchInterval:
            self.index = (self.index + 1) % (self.last-self.first) #model.numLEDs
            self.lastSwitchTime = params.time

        frame[self.first + self.index] = self.color
