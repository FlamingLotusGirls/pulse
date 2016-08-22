Soma/Pulse OPC Client
=================

A simple Python framework for rendering LED patterns and sending them to
an Open Pixel Control server.  Pulled out of [Mens Amplio][mensamplio] for
extension and re-use in future projects.

[mensamplio]: https://github.com/mens-amplio/mens-amplio
[opc]:        https://github.com/FlamingLotusGirls/openpixelcontrol

Simulator
=========

To develop patterns for Soma (or Pulse), you can first run them in an OpenGL simulator on
a Linux or OSX desktop:

* Clone this repository

* In the same top-level directory, clone FLG's [fork of Open Pixel Control][opc].
  Be sure to use the FLG fork, and not the original.

* Install dependencies:

    * numpy

    * Linux also requires: mesa-common-dev, freeglut3-dev

* cd pulse/pods/opc-client

* In one window, launch the visualizer:

    * ./run-simulator.sh

* In another window, launch the client:

    * ./pod_client.py

In the visualizer, **click-and-drag** will spin the model around.
**Shift+click-and-drag** zooms in and out.  The **arrow keys** pan the
sculpture along the X and Y axis, and **PageUp** and **PageDown** moves
it along the Z axis.  To simulate button presses, press **1** for the
left-hand button, and **0** for the right-hand one.
