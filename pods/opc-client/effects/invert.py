from effectlayer import EffectLayer 
from colorsys import hsv_to_rgb, rgb_to_hsv

def invert_hue(color):
    "Invert the hue of an RGB color value"
    hsv = rgb_to_hsv(*color)
    hsv = (abs(hsv[0] - 0.5), hsv[1], hsv[2])
    return hsv_to_rgb(*hsv) 


class InvertColorsLayer(EffectLayer):
    """
    This layer inverts the hue of colors in the frame
    when either button is pressed.
    """
    def __init__(self):
        pass

    def render(self, model, params, frame):
        for i in range(len(frame)):
            frame[i] = invert_hue(frame[i])

class InvertColorByRegionLayer(EffectLayer):
    """
    Invert the hues of the lower and upper dodecas
    independently when buttons are pressed.
    If both are pressed simultaneously, also invert the axon.
    """

    def __init__(self, model):
        self.model = model

    def invert_region(self, frame, indexes):
        for i in indexes:
            frame[i] = invert_hue(frame[i])

    def render(self, model, params, frame):
        if (params.buttonState[0]):
            self.invert_region(frame, self.model.lowerIndices)
        if (params.buttonState[1]):
            self.invert_region(frame, self.model.upperIndices)
        if all(params.buttonState):
            self.invert_region(frame, self.model.axonIndices)


