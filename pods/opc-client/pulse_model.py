from model import *
class PulseModel(Model):
    """
    The model has the following members, taken from the 'points.json' file (or whatever file
    you decide to load):
    - rawPoints. Array of raw positions, unscaled.
    - nodes. Array of scaled positions - coordinates have been scaled to [0,1]
    - pointNames. Array of names of LEDs - A12, U15C, etc
    - axonIndices. Array of indices for axons LEDs
    - lowerIndices. Array of indices for the lower dendrite
    - upperIndices. Array of indices for the upper dendrite
    - addresses. Array of indices of R485 protocol addresses, if address_filename is specified (really handy for debugging on the actual sculpture)
    """

    def __init__(self, points_filename='points.json', address_filename=None):
        self.json = json.load(open(points_filename))


        # if there is an addresses file, read it
        if address_filename:
           self.addresses = self._addressesRead(address_filename)
           print("have %d addresses" %(len(self.addresses)))
        else:
           self.addresses = None
        
        # pull raw positions from JSON
        self.rawPoints = self._nodesFromJSON()

        Model.__init__(self, len(self.rawPoints))

        # get names of points
        self.pointNames = self._namesFromJSON()

        #sort points into regions
        self.regionIndicies = {}
        for i in range(len(self.json)):
            region = self.json[i]['region']
            idx_list = self.regionIndicies.setdefault(region, [])
            idx_list.append(i)


        # get indices of nodes in different portions of the sculpture
        self.axonIndices = self._getAxonIndices()
        self.lowerIndices = self._getLowerIndices()
        self.upperIndices = self._getUpperIndices()

        # Axis-aligned bounding box, for understanding the extent of the coordinate space.
        # The minimum and maximum are 3-vectors in the same coordinate space as self.nodes.
        self.minAABB = [ min(v[i] for v in self.rawPoints) for i in range(3) ]
        self.maxAABB = [ max(v[i] for v in self.rawPoints) for i in range(3) ]

        # # Scaled Nodes: It's easier to work with coordinates in the range [0, 1], so scale them according
        # # to the AABB we discovered above.
        self.nodes = numpy.array([[ (v[i] - self.minAABB[i]) / (self.maxAABB[i] - self.minAABB[i]) for i in range(3) ] for v in self.rawPoints])

        # self._testPrint()

    def _namesFromJSON(self):
        names = [];
        for val in self.json:
            names.append(val['name'])
        return names

    def _nodesFromJSON(self):
        points = []
        for val in self.json:
            points.append(val['point'])
        return numpy.array(points)

    def _getAxonIndices(self):
        k = 'Axon'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _getLowerIndices(self):
        k = 'Lower'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _getUpperIndices(self):
        k = 'main region'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _addressesRead(self, addressFilename):
        tmpAddresses = []
        with open(addressFilename, 'r') as file:
           for line in file:
              if line[0] !='#' and not line.isspace():
                 tmpAddresses.append(line)
        print "Found %d addresses" %(len(tmpAddresses))
        return tmpAddresses

    def _testPrint(self):
        print self.upperIndices
        # print self.rawPoints[self.upperIndices]
