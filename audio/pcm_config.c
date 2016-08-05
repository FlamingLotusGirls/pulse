#include <arpa/inet.h>
#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "pcm_config.h"
#include "pcm_utils.h"
#include "wav.h"
#include "linked_list.h"

// Read configuration file and load the various heartbeat sounds
// file format is defined as: <filename>, validRateStart, validRateEnd
// Both valid rate start and valid rate end are integers

static LinkedList *hbSoundList = NULL;

static PcmData *m_BreathingData = NULL;

#define NUMBER_TRANSIENTS 1
static PcmData m_transients[NUMBER_TRANSIENTS];
static const char *m_transient_filenames[NUMBER_TRANSIENTS] = {"kaboom16.wav"};
//static const char *m_transient_filenames[NUMBER_TRANSIENTS] = {"speakertest.wav"};


// WAV parsing
static unsigned char *extractPCMFromWAV(unsigned char *wavData, int datalen, int *pcmDataLen);
static void mungeWAVHeader(WAV_Header *header);
static int pcmReadData(const char *filename, PcmData *data);
static void releaseSound(HbData *sound);

#define BREATHING_FILE_NAME "breathing1.wav"


void PcmConfig_Shutdown()
{
    while (hbSoundList) {
        LinkedList *next = hbSoundList->next;
        if (hbSoundList->data) {
            releaseSound((HbData *)hbSoundList->data);
        }
        free(hbSoundList);
        hbSoundList = next;
    }
    //XXX release breathing and transient sounds
}

static void releaseSound(HbData *sound)
{
    if (sound) {
        if (sound->filename) {
            free(sound->filename);
            sound->filename = NULL;
        }
        free(sound);
    }
}

int PcmConfig_Read()
{
    char strBuf[255];
    FILE *configFile = fopen(HB_CONFIG_FILE, "r");
    if (configFile <=0) {
        printf("Error reading file %s: %s\n", HB_CONFIG_FILE, strerror(errno));
        return ERR_FILE_NOT_FOUND;
    }
    
    while (fgets(strBuf, 255, configFile)) {
        char *strPtr = strBuf;
        // skip past space
        while (*strPtr != '\0' && isspace(*strPtr)) {
            strPtr++;
        }
        if (*strPtr == '#') {
            continue;
        }
        printf("Read config file, line %s", strBuf);
        
        char *tokStr = strPtr;
        char *filename = NULL;
        int  validFreqStart = 0;
        int  validFreqEnd   = 0;
        while ((strPtr = strtok(tokStr, ",")) != NULL) {
            tokStr = NULL;
            if (!filename) {
                filename = strPtr;
                printf("filename is %s\n", filename);  // XXX watch it with the filename. It goes out of scope - this ain't java
                
                continue;
            }
            if (!validFreqStart) {
                validFreqStart = atoi(strPtr);
                if (validFreqStart == -1) {
                    printf("Invalid frequency %s in config file\n", strPtr);
                    break;
                }
                printf("freqStart is %d\n", validFreqStart);
                continue;
            }
            
            if (!validFreqEnd) {
                validFreqEnd = atoi(strPtr);
                if (validFreqEnd == -1) {
                    printf("Invalid frequency %s in config file\n", strPtr);
                    break;
                }
                printf("freqEnd is %d\n", validFreqEnd);
                
                // at this point, we should have all valid values for this entry.
                // Add to linked list
                HbData *data = (HbData *)malloc(sizeof(HbData));
                if (!data) {
                    printf("Error out of memory\n");
                    break;
                }

                data->filename = (char *)malloc(strlen(filename) + 1);
                if (!data->filename) {
                    printf("Error our of memory\n");
                    break;
                }
                strcpy(data->filename, filename);
                data->filename = filename;
                data->data = NULL;
                data->validFreqStart = validFreqStart;
                data->validFreqEnd   = validFreqEnd;
                hbSoundList = LinkedListAdd(hbSoundList, data);
                continue;
            }
        }
        
        // at this point we should have our list of heartbeat sounds. Now read them in
        LinkedList *entry = hbSoundList;
        while (entry) {
            HbData *sound = (HbData *)(entry->data);
            if (sound && sound->filename && !sound->data) {
                FILE *dataFile = fopen(sound->filename, "rb");
                char *filedata = NULL;
                if (!dataFile) {
                    printf("Could not open heartbeat data file %s\n", sound->filename);
                    goto hb_sounds_iterate;
                }
                int fd = fileno(dataFile);
                if (fd < 0) {
                    printf("Heartbeat data file invalid %s\n", sound->filename);
                    goto hb_sounds_iterate;
                }
                struct stat sb;
                if (fstat(fd, &sb) != 0) {
                    printf("Could not stat file %s\n", sound->filename);
                    goto hb_sounds_iterate;
                }
                int filesize = sb.st_size;
                if (filesize <= 0) {
                    printf("Heartbeat data file size invalid %s, %d bytes\n", sound->filename, filesize);
                    goto hb_sounds_iterate;
                }
                sound->datalen = filesize;
                filedata = (char *)malloc(filesize);
                if (!filedata) {
                    printf("Could not allocate memory (%d bytes) for file %s\n", filesize, sound->filename);
                    goto hb_sounds_iterate;
                }
                
                int elemRead = fread(filedata, filesize, 1, dataFile);
                if (elemRead != 1) {
                    printf("Error reading data from file %s\n", sound->filename);
                    goto hb_sounds_iterate;
                }
                
                int dataLen = 0;
                unsigned char *pcmData = extractPCMFromWAV((unsigned char *)filedata, filesize, &dataLen);
                if (!pcmData) {
                    printf("Could not extract PCM data from file %s\n", sound->filename);
                    goto hb_sounds_iterate;
                }
                
                sound->data = (unsigned char *)pcmData;
                sound->datalen = dataLen;
hb_sounds_iterate:
                if (filedata) {
                    free(filedata);
                }
                if (dataFile) {
                    fclose(dataFile);
                }
            }
            entry = entry->next;
        }
    }
    
    // and let's read in our breathing file too....
    m_BreathingData = (PcmData *)malloc(sizeof(PcmData));
    if (!m_BreathingData) {
        printf("Memory allocation failure\n");
        goto Exit;
    }
    
    m_BreathingData->filename = strdup(BREATHING_FILE_NAME);
    if (!m_BreathingData->filename) {
        printf("Memory allocation failure\n");
        goto Exit;
    }
        
    if (pcmReadData(BREATHING_FILE_NAME, m_BreathingData) != 0){
        printf("Error reading breathing data\n");
        // XXX - not errorring out just yet since I don't actually have breathing data FIXME
    }
    
    // and a transient
    PcmData *transient = &m_transients[0];
    transient->filename = strdup(m_transient_filenames[0]);
    if (pcmReadData(transient->filename, transient) != 0) {
        printf("Error reading transient data\n");
        // XXX - not errorring out just yet since I don't actually have proper transient data FIXME
    }
    
Exit:
    fclose(configFile);
    
    return 0;
}

static int pcmReadData(const char *filename, PcmData *data)
{
    FILE *dataFile = fopen(filename, "rb");
    char *filedata = NULL;
    if (!dataFile) {
        printf("Could not open sound data file %s\n", filename);
        goto ErrorExit;
    }
    int fd = fileno(dataFile);
    if (fd < 0) {
        printf("Sound data file invalid %s\n", filename);
        goto ErrorExit;
    }
    struct stat sb;
    if (fstat(fd, &sb) != 0) {
        printf("Could not stat file %s\n", filename);
        goto ErrorExit;
    }
    int filesize = sb.st_size;
    if (filesize <= 0) {
        printf("Heartbeat data file size invalid %s, %d bytes\n", filename, filesize);
        goto ErrorExit;
    }
    filedata = (char *)malloc(filesize);
    if (!filedata) {
        printf("Could not allocate memory (%d bytes) for file %s\n", filesize, filename);
        goto ErrorExit;
    }
    
    int elemRead = fread(filedata, filesize, 1, dataFile);
    if (elemRead != 1) {
        printf("Error reading data from file %s\n", filename);
        goto ErrorExit;
    }
    
    int dataLen = 0;
    unsigned char *pcmData = extractPCMFromWAV((unsigned char *)filedata, filesize, &dataLen);
    if (!pcmData) {
        printf("Could not extract PCM data from file %s\n", filename);
        goto ErrorExit;
    }
    
    data->data = pcmData;
    data->datalen = filesize;
//    data->filename = filename; // watch that XXX
    
    return 0;
    
ErrorExit:
    if (filedata) {
        free(filedata);
    }
    if (dataFile) {
        fclose(dataFile);
    }
    return -1;
}

// Iterate list of heartbeat sounds, looking for the right one
// Note that we return the *last* matching sound, rather than the first one.
// This allows me to easily set defaults in the config file
HbData* PcmConfig_getHbSound(int freqBPM) 
{
    LinkedList *entry = hbSoundList;
    HbData *bestSound = NULL;
//    printf("Looking for a sound with frequency %d\n", freqBPM);
    while (entry) {
        HbData *sound = (HbData *)(entry->data);
//        printf("Sound start freqstart is %d, end is %d\n", sound->validFreqStart, sound->validFreqEnd);
        if (sound && sound->validFreqStart <= freqBPM && sound->validFreqEnd >= freqBPM) {
            bestSound = sound;
        }
        entry = entry->next;
    }
    return bestSound;
}

PcmData *PcmConfig_getBreathingSound()
{
    return m_BreathingData;
}


PcmData *PcmConfig_getTransientSound(TransientSoundType type)
{
    return &m_transients[0]; // XXX match with transient sound types!!
}


static char RIFF[4] = {'R', 'I', 'F', 'F'};
static char WAVE[4] = {'W', 'A', 'V', 'E'};
static char FMT_[4] = {'f', 'm', 't', ' '};
static char DATA[4] = {'d', 'a', 't', 'a'};
 
static unsigned char *extractPCMFromWAV(unsigned char *wavData, int datalen, int *pcmDataLen)
{
    if (datalen <= sizeof(WAV_Header)) {
        printf("Invalid WAV file, cannot parse\n");
        return NULL;
    }
    
    WAV_Header *header = (WAV_Header *)wavData;
    mungeWAVHeader(header);

    if (memcmp(RIFF, (unsigned char *)&header->RIFF_ID, 4)) {
        printf("Invalid WAV file, bad RIFF header\n");
        return NULL;
    }

    if (memcmp(WAVE, (unsigned char *)&header->WAVEID, 4)) {
        printf("Invalid WAV file, bad WAVE header\n");
        return NULL;
    }
    
    // Now let's find the format and data chunks...
    FmtChunk *fmtChunk  = NULL;
    unsigned char *data_block = NULL;
    unsigned char *wavPtr = ((unsigned char *)header) + sizeof(WAV_Header);
    while (!(fmtChunk && data_block) && (wavPtr < wavData + datalen)) {
        printf("Found chunk (%c%c%c%c)\n", *wavPtr, *(wavPtr+1), *(wavPtr+2), *(wavPtr+3));
        if (!memcmp(FMT_, wavPtr, 4)) {
            fmtChunk = (FmtChunk *)wavPtr;
        } else if (!memcmp(DATA, wavPtr, 4)){
            data_block = wavPtr;
        } 
        wavPtr += 8 + *(uint32_t *)(wavPtr + 4); // skip header and following block
    }
    if (!(fmtChunk && data_block)) {
        printf("Invalid WAV file, could not find format and data chunks\n");
        return NULL;
    }
    
    if (fmtChunk->wBitsPerSample != 16) {
        printf("Not 16 bits per sample (%d). Rejecting\n", fmtChunk->wBitsPerSample);
        return NULL;
    }
    
    if (fmtChunk->nSamplesPerSec != 44100) {
        printf("Not 44.1K samples per second (%d), rejecting\n", fmtChunk->nSamplesPerSec);
        return NULL;
    }
   
   /*  XXX FIXME - should be mono!!
    if (fmtChunk->nChannels != 1) {
        printf("Not mono (%d). Rejecting\n", fmtChunk->nChannels);
        return NULL;
    }
    */
    
    uint32_t dataSize = *(uint32_t *)(data_block + 4);
    //dataSize = ~htonl(dataSize);

    // allocate data, return copy of data from 
    unsigned char *pcmData = (unsigned char *)malloc(dataSize);
    if (!pcmData) {
        printf("Could not allocate memory for pcm buffer\n");
        return NULL;
    }

    memcpy(pcmData, data_block + 8, dataSize);
    
    if (pcmDataLen) {
        *pcmDataLen = dataSize;
    }
    return pcmData;
}

/*

Ah, this is fucked. WAV byte is little endian, but network byte order is big endian. What
we need here to make this code actually portable is ~ntoh functions - ie, little endian to host.
At the moment, though, since the pi is also little endian, simply making this function do
nothing works fine. 

It's also important to note that the last three fields may not actually be in this chunk...
Need to check cksize before munging them.
*/

static void mungeWAVHeader(WAV_Header *header) {
/*
    assert(header);
    header->cksize                   = ntohl(header->cksize);
    //header->fmtChunk.cksize          = ntohl(header->fmtChunk.cksize);
    //header->fmtChunk.wFormatTag      = ntohs(header->fmtChunk.wFormatTag);
    //header->fmtChunk.nChannels       = ntohs(header->fmtChunk.nChannels);
    //header->fmtChunk.nSamplesPerSec  = ntohl(header->fmtChunk.nSamplesPerSec);
   
//    header->fmtChunk.nAvgBytesPerSec = ntohl(header->fmtChunk.nAvgBytesPerSec);
//    header->fmtChunk.nBlockAlign     = ntohs(header->fmtChunk.nBlockAlign);
    //header->fmtChunk.wBitsPerSample  = ntohs(header->fmtChunk.wBitsPerSample);
//    header->fmtChunk.cbSize          = ntohs(header->fmtChunk.cbSize);
//    header->fmtChunk.wValidBitsPerSample  = ntohs(header->fmtChunk.wValidBitsPerSample);
    header->fmtChunk.dwChannelMask   = ntohl(header->fmtChunk.dwChannelMask);
*/

}


