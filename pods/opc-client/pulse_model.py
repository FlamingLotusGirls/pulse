from model import *

LEDS_PER_POINT = 9

class PulseModel(Model):
    """
    The model has the following members, taken from the 'points.json' file (or whatever file
    you decide to load):
    - rawPoints. Array of raw positions, unscaled.
    - nodes. Array of scaled positions - coordinates have been scaled to [0,1]
    - pointNames. Array of names of LEDs - A12, U15C, etc
    - branch1. Array of indices for branch1
    - branch2. Array of indices for branch1
    - branch3. Array of indices for branch1
    - branch4. Array of indices for branch1
    
    Also note that, unlike Soma, there isn't a one to one mapping between the nodes in the
    model and the LEDs for OPC. In Pulse, there are 9 individual LEDs per bulb.
    """


    def __init__(self, points_filename='points.json'):
        self.json = json.load(open(points_filename))

        # pull raw positions from JSON
        self.rawPoints = self._nodesFromJSON()

        Model.__init__(self, len(self.rawPoints))

        # get names of points
        self.pointNames = self._namesFromJSON()

        #sort points into regions
        self.regionIndicies = {}
        for i in range(len(self.json)):
            for idx in range(LEDS_PER_POINT): # we have 9 LEDs per point in the model
                region = self.json[i]['region']
                idx_list = self.regionIndicies.setdefault(region, [])
                idx_list.append(i)
        self.allIndices = self.regionIndicies.values()

        # get indices of nodes in different portions of the sculpture
        self.branch1Indices = self._getBranch1Indices()
        self.branch2Indices = self._getBranch2Indices()
        self.branch3Indices = self._getBranch3Indices()
        self.branch4Indices = self._getBranch4Indices()
        
        print "number of branch1 indices is ", len(self._getBranch1Indices())

        # Axis-aligned bounding box, for understanding the extent of the coordinate space.
        # The minimum and maximum are 3-vectors in the same coordinate space as self.nodes.
        self.minAABB = [ min(v[i] for v in self.rawPoints) for i in range(3) ]
        self.maxAABB = [ max(v[i] for v in self.rawPoints) for i in range(3) ]

        # # Scaled Nodes: It's easier to work with coordinates in the range [0, 1], so scale them according
        # # to the AABB we discovered above.
        self.nodes = numpy.array([[ (v[i] - self.minAABB[i]) / (self.maxAABB[i] - self.minAABB[i]) for i in range(3) ] for v in self.rawPoints])

        self._testPrint()

    def _namesFromJSON(self):
        names = [];
        for val in self.json:
            for idx in range(LEDS_PER_POINT): # we have 9 LEDs per point in the model
                names.append(val['name'])
        return names

    def _nodesFromJSON(self):
        points = []
        for val in self.json:
            for idx in range(LEDS_PER_POINT): # we have 9 LEDs per point in the model
                points.append(val['point'])
        return numpy.array(points)

    def _getBranch1Indices(self):
        k = 'branch1'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _getBranch2Indices(self):
        k = 'branch2'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _getBranch3Indices(self):
        k = 'branch3'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _getBranch4Indices(self):
        k = 'branch4'
        return self.regionIndicies[k] if k in self.regionIndicies.keys() else []

    def _testPrint(self):
        print self.branch1Indices
