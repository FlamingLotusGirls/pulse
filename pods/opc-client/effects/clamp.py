from effectlayer import EffectLayer 
from colorsys import hsv_to_rgb, rgb_to_hsv

def clamp_brightness(color, scaling_factor):
    hsv = rgb_to_hsv(*color)
    hsv = ( hsv[0], hsv[1], (hsv[2] * scaling_factor) )
    return hsv_to_rgb(*hsv)

class BrightnessStateMachineLayer(EffectLayer):
    """
    This layer constricts the dynamic range of a frame to allow
    subsequent effect layers to alter brightness for dramatic effect.
    """

    LOWER_EXCITATION_OFF = 0.4
    LOWER_EXCITATION_INCREMENT = 0.1
    UPPER_EXCITATION_OFF = 0.4
    UPPER_EXCITATION_INCREMENT = 0.3
    AXON_EXCITATION_OFF = 0.2
    NUM_FRAMES_TO_FIRE = 40
    NUM_FRAMES_TO_SPAZ = 120

    def __init__(self):
        self.button_zero_was_up = True
        self.button_one_was_up = True
        self.lower_excitation = self.LOWER_EXCITATION_OFF
        self.upper_excitation = self.UPPER_EXCITATION_OFF
        self.firing = False
        self.firing_frames = 0
        self.spazzing = False
        self.spaz_frames = 0

    def clamp_region(self, frame, indexes, scaling_factor):
        for i in indexes:
            frame[i] = clamp_brightness(frame[i], scaling_factor)

    def render(self, model, params, frame):
        if self.spazzing:
            if self.spaz_frames > self.NUM_FRAMES_TO_SPAZ:
                self.spazzing = False
            else:
                self.spaz_frames += 1
            # effects layer off - full brightness
        else:
            if (params.buttonState[0] and self.button_zero_was_up):
                self.lower_excitation += self.LOWER_EXCITATION_INCREMENT
                self.button_zero_was_up = False
                if (params.buttonState[1]): # two player bonus
                    self.lower_excitation += self.LOWER_EXCITATION_INCREMENT*3
                    self.button_one_was_up = False
            elif not params.buttonState[0]:
                self.button_zero_was_up = True

            if (params.buttonState[1] and self.button_one_was_up):
                self.lower_excitation += self.LOWER_EXCITATION_INCREMENT
                self.button_one_was_up = False
                if (params.buttonState[0]): # two player bonus
                    self.lower_excitation += self.LOWER_EXCITATION_INCREMENT*3
                    self.button_zero_was_up = False
            elif not params.buttonState[1]:
                self.button_one_was_up = True

            if self.lower_excitation > 1.0:
                self.firing = True

            if self.upper_excitation > 1.0:
                self.spazzing = True
                self.upper_exctation = self.UPPER_EXCITATION_OFF
                self.lower_excitation = self.LOWER_EXCITATION_OFF

            if self.firing:
                if self.firing_frames > self.NUM_FRAMES_TO_FIRE:
                    self.firing = False
                    self.firing_frames = 0
                    self.lower_excitation = self.LOWER_EXCITATION_OFF
                    self.upper_excitation += self.UPPER_EXCITATION_INCREMENT
                else:
                    self.firing_frames += 1

            self.clamp_region(frame, model.lowerIndices, self.lower_excitation)

            self.clamp_region(frame, model.upperIndices, self.upper_excitation)

            if self.firing:
                self.clamp_region(frame, model.axonIndices, 1.0)            
            else:
                self.clamp_region(frame, model.axonIndices, self.AXON_EXCITATION_OFF)
