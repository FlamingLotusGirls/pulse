import time
import numpy

class Fade:
    """
    Renders a smooth transition between multiple lists of effect layers
    """
    def __init__(self, startLayers, endLayers):
        self.done = False # should be set to True when fade is complete
        self.startLayers = startLayers
        self.endLayers = endLayers # final layer list to be rendered after fade is done
    
    def render(self, model, params, frame):
        raise NotImplementedException("Implement in fader subclass")
        
        
class LinearFade(Fade):
    """
    Renders a simple linear fade between two lists of effect layers
    """
    def __init__(self, startLayers, endLayers, duration):
        Fade.__init__(self, startLayers, endLayers)
        self.duration = float(duration)
        # set actual start time on first call to render
        self.start = None
        
    def render(self, model, params, frame):
        if not self.start:
            self.start = time.time()
        # render the end layers
        if self.endLayers:
            for layer in self.endLayers:
                layer.safely_render(model, params, frame)
        percentDone = (time.time() - self.start) / self.duration
        if percentDone >= 1:
            self.done = True
        else:
            # if the fade is still in progress, render the start layers
            # and blend them in
            numpy.multiply(frame, percentDone, frame)
            if self.startLayers:
                frame2 = numpy.zeros(frame.shape)
                for layer in self.startLayers:
                    layer.safely_render(model, params, frame2) 
                numpy.multiply(frame2, 1-percentDone, frame2)
                numpy.add(frame, frame2, frame)
            
            
class TwoStepFade(Fade):
    def __init__(self, fade1, fade2, startLayers, endLayers):
        Fade.__init__(self, startLayers, endLayers)
        self.fade1 = fade1
        self.fade2 = fade2
    
    def render(self, model, params, frame):
        if not self.fade1.done:
            self.fade1.render(model, params, frame)
        else:
            self.fade2.render(model, params, frame)
            self.done = self.fade2.done
            
            
class FastFade(TwoStepFade):
    """
    Fade from startLayers to nothing, then from nothing to endLayers. This should be
    more efficient than fading directly between two layer sets because we 
    never have to render both layer sets at the same time.
    """
    def __init__(self, startLayers, endLayers, duration):
        fade1 = LinearFade(startLayers, None, duration/2.)
        fade2 = LinearFade(None, endLayers, duration/2.)
        TwoStepFade.__init__(self, fade1, fade2, startLayers, endLayers)

            
class TwoStepLinearFade(TwoStepFade):
    """
    Performs a linear fade to an intermediate effect layer list, then another linear
    fade to a final effect layer list. Useful for making something brief and dramatic happen.
    """
    def __init__(self, currLayers, nextLayers, finalLayers, duration_1, duration_2):
        fade1 = LinearFade(currLayers, nextLayers, duration_1)
        fade2 = LinearFade(nextLayers, finalLayers, duration_2)
        TwoStepFade.__init__(self, fade1, fade2, currLayers, finalLayers)