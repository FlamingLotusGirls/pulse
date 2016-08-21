import math
import random
import numpy
from effectlayer import *
import png
import glob

class PhotoColorsLayer(EffectLayer):

    def __init__(self, model):
        images = glob.glob("images/*.png")
        self.image = random.choice(images)
        self.file = open(self.image)
        reader = png.Reader(self.file)
        self.lastFrame = None
        print "reading photo"
        photo = reader.read()
        print self.image
        print "width", photo[0]
        print "height", photo[1]
        print "metadata", photo[3]
        metadata = photo[3]
        self.alpha = metadata['alpha'] # Boolean indicates the presense of an alpha channel.
        self.photoSize = photo[0] * photo[1]
        self.rows = photo[2]
        self.offset = 0
        self.pixelIter = self._pixelIter(photo)

    def _pixelIter(self, photo):
        """
        Infinitely iterate over pixels in the image.
        """
        while True:
            # Generate a new row iterator
            rowIter = photo[2]
            for row in rowIter:
                width = len(row)
                i = 0
                try:
                    while i < width:
                        r = row[i]
                        g = row[i+1]
                        b = row[i+2]
                        i += 3
                        if self.alpha:
                            i += 1
                        pixel = numpy.array((r/255.,g/255.,b/255.))
                        yield pixel
                except IndexError:
                    continue

    def render(self, model, params, frame):
        if self.lastFrame == None:
            for i in xrange(len(frame)):
               frame[i] = self.pixelIter.next()
            self.lastFrame = frame
        else:
            # add a new pixel from the stream
            frame[0] = self.pixelIter.next()
            # Shift the last frame over by one
            for i in xrange(1, len(frame)):
                frame[i] = self.lastFrame[i-1]
            self.lastFrame = numpy.copy(frame)
