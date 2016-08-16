Code for operating the Elation Professional Sixpar 200IP spotlights via a DMX
controller.

I will probably be running the spotlights on 8 channels, meaning the four
spotlights will need addresses 1, 9, 17, 25. As of writing this I have only
tested the code with two lights using 6 channels, but the logic is the same.

There are a couple of dependencies for this:

1. D2XX FTDI driver, found at http://www.ftdichip.com/Drivers/D2XX/Linux/libftd2xx-arm-v6-hf-1.3.6.tgz
Installation instruction can be found here: http://www.ftdichip.com/Drivers/D2XX/Linux/ReadMe-linux.txt

2. My fork of pySimpleDMX:
'pip install git+https://github.com/pewing/pySimpleDMX'


To run this: 'python dmx_controller.py'



-Philip 8/16/2016
