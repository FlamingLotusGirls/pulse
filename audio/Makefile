# requires the alsa libraries. The run-time is standard in linux, but
# the header files require you to download the libasound2-dev package
# (apt-get install libasound2-dev, or something similar)

LIB=-L/usr/lib -l asound2
INC=-I. -I/usr/include/alsa
CCP=g++
CC=gcc
CFLAGS = -std=gnu99 -Wall -Werror -I. -I/usr/include/alsa
LDFLAGS = -L/usr/lib -lasound -lpthread -lrt

PROJ = sound_test
OBJS = pcm_config.o pcm_sound.o sound_test.o linked_list.o

all: $(PROJ)

$(PROJ): $(OBJS)


clean: rm -f $(PROJ) $(OBJS)
