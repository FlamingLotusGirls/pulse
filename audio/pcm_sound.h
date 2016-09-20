#ifndef PCM_SOUND_H
#define PCM_SOUND_H

#include "pcm_config.h"

int pcmPlaySound(unsigned char* pcmSoundBuf, int pcmBufLen, unsigned int freqMs, int channels, unsigned char volume, const char *name);
//int pcmPlaySound(unsigned char* pcmSoundBuf, int pcmBufLen, unsigned int freqMs);
void pcmPlayHeartBeat(unsigned int freqBPS, unsigned char volume, unsigned int timeOffset);
//void pcmPlayHeartBeat(unsigned int freqBPS, unsigned char volume);
void pcmPlayBreathing(unsigned int freqBPS, unsigned char volume);
void pcmPlaySpecial(TransientSoundType soundId, unsigned char volume);
int pcmPlaybackInit(void);
int pcmPlaybackStop(void);

#endif //PCM_SOUND_H