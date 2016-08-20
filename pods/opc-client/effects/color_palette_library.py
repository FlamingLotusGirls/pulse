# import math
import random
import numpy
# from effectlayer import *
# from effects.color_palette_library import *
# import random

class ColorPaletteLibrary:

    def __init__(self):
        self.palettes = [
            [0x4CFF00, 0x009BC2, 0x85E7FF, 0x00CCFF, 0xB300FF],
            [0x33AA99, 0x66EE88, 0x00DDFF, 0x22FFFF, 0xFFEE55],
            [0x4C2A14, 0xEC5A00, 0xFFA200, 0xFFFF00, 0xFFFFC3],
            [0x62A9F0, 0x517506, 0x68C51C, 0xBEB940, 0xEDFA25],
            [0x8AC97B, 0xE8AFBA, 0xE8C1AF, 0xDDAFE8, 0x6BB1D1],
            [0x45B29D, 0xE27A3F, 0xDF4949, 0xE8B37D, 0xEFC94C]
        ]
        
    def getPalette(self):
        randomPalette = random.choice(self.palettes)
        return self.generatePalette(randomPalette)

    def generatePalette(self, hexValues):
        def convertColor(val):
            r = (val & 0xff0000) >> 16
            g = (val & 0x00ff00) >> 8
            b = (val & 0x0000ff)
            return numpy.array([r/255., g/255., b/255.]) 

        return [ convertColor(val) for val in hexValues ] 

