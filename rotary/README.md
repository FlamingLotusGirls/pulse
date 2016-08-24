# Rotary code

Original code written / stolen by Brian Bulkowski Aug 2016
Contact: brian@bulkowski.org

## Prerequsite

This code assume a Jessie Raspberrian distribution. It uses Python3 ( and is thus generica code that probably works under Python 2.7 and above ).

The python library is GPIO. This appears to be fully installed on recent ( 2016 ) Raspberrian releases of Jessie. No extra install is required. ( There is some stuff on the internet about enabling "devicetree" but in my installs, "devicetree" is enabled by default ). 

## Overview

Some interactions like dials. 

There are two fundamential kinds of digital dials: rotary switches, and rotary encoders.

A rotary switch has a number of connectors out the bottom, and bridge the connectors based on the position of the dial. For that kind of connector, see the code in 4switch.py . You need a GPIO line for every switch position.

A rotary encoder has two internal switches and "detents". The shaft goes around 360 degrees and continues to rotate. Each detent opens and closes the two switches. There is a set of values, but you have no view of absolute rotation. The benefit is only 2 lines of GPIO are needed to cover full rotation - and the knob moves pretty smoothly. For further information, see below.

## Rotary switches

The code it written to work with a knob that has four positions. The knob I had is actually a 3 pole switch, but only wired one. The "central connector" is wired to Ground ( because generally ground is more available on a raspberry pi ), and the other switch positions are wired to GPIO lines ( which can be modified at the top of the file ).

The code is more of a proof of concept. Better structured code would use an object, and have general code that allows loading in the pins, and support arbitrary number of pins, and probably an event-oriented callback system ( see the "bobrathbone" structure of dealing with rotary encoders ).

Without knowing how this code would be embedded, I didn't want to lard it up with structure ( yet ).

## Rotary encoders

A rotary encoder has three main contacts - A and B and C ( C is in the middle ). The wiring is to put C to ground, and A and B to GPIO pins. Encoders use something called Grey Encoding, which is the peculiar code you'll see. The code attempts to have a "value" where 0 is the initial position when the python script is launched, then attempt to print out when each detent is rotated.

A detent becomes essential 4 transition state changes. Depending on the transitions, that determines whether the switch is rotating clockwise or counterclockwise.

In testing, you'll see that just turning the knob a little bit, you'll see one of the two switches move a little. You want to watch both A and B switches, and make sure both move in order to decide the value changes - thus this code "debounces" a bit.

There are also questions about what to do if you think you've missed some switch positions. In the timing that's in this code, I did not see any issues.

Finally, I encluded the Bob Rathbone code, because it has a rather pleasant callback interface and an event oriented system. I ended up disabling this because I wanted to see if that was at risk for missing positions. If I was to move the code forward, I would consider moving back to the event oriented structure. I also tried things like specific GC calls - which don't seem necessary.

### A note about switches

Some rotary encoder packackages also have a "push to click" capability. In the "bobrathbone" code ( which can also be found on the internet ), you'll see a bunch of that, which is also very useful. However, the exact encoders that were available to me did not have this switch, so I stripped it from the code.

### a note about `print_test.py`

In testing, I found that the switch states were "laggy" in printouts. That's why you'll see timestamps on the print outs - it shows that internally, the Python code isn't laggy.

The `print_test.py` code also shows the lag, without using switches. You might use it to debug whether your RPI also has this laggy SSH.

