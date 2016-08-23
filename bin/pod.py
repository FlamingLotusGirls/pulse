#!/usr/bin/env python

import os
import sys
# HACK: all of these dirs (dmx/pods/etc) should really be separate python packages
# just gonna append project root to PYTHONPATH so we can import in a predictable manner
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             '../pods/opc-client')))
import pod_client # should really be a class that init's self if run from cli (__name == __main__)
pod_client.main()
