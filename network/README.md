Python code for sending and receiving over the Pulse network.

The controller code is intended for 'production', that is, it
should run on the Raspberry Pi that runs the heart fire effects. 
It listens for heartbeats and commands

The server code is test code - the actual  heartbeats will be generated
by a Pi connected to a biosensor. 

Additional controller modules should be added for lighting and sound
effects. Lighting and sound may be driven off of the same Pi if processing
allows, although the two pulse pods will be controlled by separate systems

-CSW, 7/13/2016
