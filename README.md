# Pulse Project

What we've got here:

* BPM - Code to detect heartbeats and put the pulses out on the network<br>
* avr - Code that runs on the 8-output relay driver boards (see eagle files in flg-svn)<br>
* avr-proportional - code that runs on the proportional valve driver board (no eagle files ... yet)<br>
* test-proportional - Android code for running the proportional valve driver board. Can run on any android device, requires standard FTDI USB to 485 cable to connect with board<br>
* testApp - Android and PC code for running the 8-output relay driver board. Can run on any android device, or web interface + python can run on Mac/Linux box. Requires standard FTDI USB to 485 cable to connect with board
* audio - Sketches for ALSA audio drivers, incomplete<br>
* network - multicast listener for heartbeats, controls relay board to send heartbeat and other patterns. Python, runs on RPi and Mac (intended for RPi in the sculpture)<br>
* dmx - Code for operating the Elation Professional Sixpar 200IP spotlights via a DMX controller

Still to do:<br>
* LEDs. Lighting for pulse pods<br>
* Mobile Interactive. Code for whatever games on mobile interactive unit<br>
* Geek console. UI, controls for the geeks back at the geek table.<br>

* Pod_daemon    A daemon run at startup that coordinates the heartbeat sensor (BPM), POD LED's, and audio
* MIU_daemon    A daemon run at startup that communicates with two heartbeat sensors (BPM), triggers LED fx, and sends out UDP packets
* Heart_daemon  A daemon run at startup that listens to udp packets from two PODs and the MIU sensors

