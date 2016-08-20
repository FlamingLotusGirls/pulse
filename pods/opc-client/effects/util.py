import random
import numpy as np
from colorsys import hsv_to_rgb, rgb_to_hsv

def jitter(size=0.15):
    return random.random() * size - (size/2)

def randomColor():
    return np.array(hsv_to_rgb(random.random(),0.75+jitter(0.5),1))

def hsvColorAdd(npRgbColor, hsv):
    """
    Add a hsv tuple to a color expressed an RGB numpy array
    Return an RGB numpy array value.
    """
    hsv1 = rgb_to_hsv(*tuple(npRgbColor))
    newhsv = np.array(hsv1) + np.array(hsv)
    return np.array(hsv_to_rgb(*tuple(newhsv)))

def colorJitter(hue_jitter=0.1, sat_jitter=0.5, val_jitter=0.5):
    return ( jitter(hue_jitter) % 1.0, jitter(sat_jitter), jitter(val_jitter) )