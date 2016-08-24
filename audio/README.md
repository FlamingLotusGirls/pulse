Code to use the low-level ALSA drivers to play sound effects with very low
latency (and a high level of control)

As of this writing, this code compiles, but it would be a miracle if it ran.
It's not finished and I don't know whether it's even going to be used (if
we can use a higher-level Python interface for this, we should) but I'm adding
it to github in case we need to work with it.

-CSW 7/13/2016

The asound.conf file needs to be placed in the /etc/ directory in order for
audio to default to the UCA202. This has already been done and shouldn't need 
to be repeated

-Philip 8/20/2016
