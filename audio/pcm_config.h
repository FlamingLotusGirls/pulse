#ifndef PCM_CONFIG_H
#define PCM_CONFIG_H

#define HB_CONFIG_FILE "/home/flaming/pulse/audio/hbconfig.conf"
#define HOME_DIR "/home/flaming/pulse/audio/"

typedef struct {
    char          *filename;
    unsigned char *data;
    int            datalen;
    int            validFreqStart;
    int            validFreqEnd;
} HbData;


// All PCM data is assumed to be 44100, 16b, mono
typedef struct {
    char          *filename;
    unsigned char *data;
    int            datalen;
} PcmData;


typedef enum {
    SOUND_CLUCK,
    SOUND_SIGH,
    SOUND_SNIFFLE,
    SOUND_MURMUR,
    SOUND_KABOOM,
} TransientSoundType;

int PcmConfig_Read();
HbData* PcmConfig_getHbSound(int freq);
PcmData *PcmConfig_getBreathingSound();
PcmData *PcmConfig_getTransientSound(TransientSoundType type);

#endif // PCM_CONFIG_H

