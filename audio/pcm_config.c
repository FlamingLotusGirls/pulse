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

// Read configuration file and load the various heartbeat sounds
// file format is defined as: <filename>, validRateStart, validRateEnd
// Both valid rate start and valid rate end are integers

typedef struct __LinkedList{
    struct __LinkedList *next;
    void *data;
} LinkedList;

static LinkedList *hbSoundList = NULL;


// WAV parsing
static unsigned char *extractPCMFromWAV(unsigned char *wavData, int datalen, int *pcmDataLen);
static void mungeWAVHeader(WAV_Header *header);


static LinkedList* LinkedListAdd(LinkedList *list, void *data)
{
    LinkedList *newList = (LinkedList *)malloc(sizeof(LinkedList));
    newList->data = data;
    newList->next = NULL;

    if (!list) {
        return newList;
    }
    
    LinkedList *tail;
    LinkedList *curElement = list;
    while(curElement) {
       tail = curElement; 
       curElement = curElement->next;
    }
    
    tail->next = newList;
    
    return list;
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
        printf("Read config file, line %s\n", strBuf);
        
        char *tokStr = strPtr;
        char *filename = NULL;
        int  validFreqStart = 0;
        int  validFreqEnd   = 0;
        while ((strPtr = strtok(tokStr, ",")) != NULL) {
            tokStr = NULL;
            if (!filename) {
                filename = strPtr;
                printf("filename is %s\n", filename);
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
    
    fclose(configFile);
    return 0;
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

    if (memcmp(FMT_, (unsigned char *)&header->fmtChunk.ckID, 4)) {
        printf("Invalid WAV file, bad FMT header\n");
        return NULL;
    }

    if (header->fmtChunk.wFormatTag != WAV_FORMAT_PCM) {
        printf("Not a PCM file (0x%x), rejecting\n", header->fmtChunk.wFormatTag);
        return NULL;
    }

    if (header->fmtChunk.wBitsPerSample != 16) {
        printf("Not 16 bits per sample (%d). Rejecting\n", header->fmtChunk.wBitsPerSample);
        return NULL;
    }
    
    if (header->fmtChunk.nSamplesPerSec != 44100) {
        printf("Not 44.1K samples per second (%d), rejecting\n", header->fmtChunk.nSamplesPerSec);
        return NULL;
    }
   
    if (header->fmtChunk.nChannels != 1) {
        printf("Not mono (%d). Rejecting\n", header->fmtChunk.nChannels);
        return NULL;
    }
    
    // all should be well at this point. check the final data block
    int headerSize = 12 + 8 + header->fmtChunk.cksize; // 12 byte RIFF header, 8 byte fmt header, and ftm chunk
    if (headerSize >= datalen) {
        printf("No data in file.\n");
        return NULL;
    }
    printf("fmtChunk size is %d\n", header->fmtChunk.cksize);
    
    // Now let's wade through the remaining chunks, looking for 'data'
    unsigned char *curPtr = wavData + headerSize;
    unsigned char *data_block = NULL;
    while ((curPtr - wavData) + 8 < datalen) {
        uint32_t blockLen = *(uint32_t *)(curPtr + 4);
        printf("Found block %c%c%c%c\n", *curPtr, *(curPtr+1), *(curPtr+2), *(curPtr+3));
//        printf("Found block size 0x%x\n", blockLen);
//        printf("Found block size %d\n", blockLen);
        if (blockLen == 0) {
            return NULL;
        }
        if (!memcmp(DATA, curPtr, 4)) {
            data_block = curPtr;
            break;
        }
        curPtr += 8 + blockLen;
    } 
    
    if (!data_block) {
        printf("data block not found\n");
        return NULL;
    }
    uint32_t dataSize = *(uint32_t *)(data_block + 4);
    //dataSize = htonl(dataSize);
    if ((data_block - wavData) + 8 + dataSize > datalen) {
        printf("Invalid file - data is %d, but only %d bytes\n", dataSize, datalen - headerSize - 9);
        return NULL;
    }
    

    // allocate data, return copy of data from 
    unsigned char *pcmData = (unsigned char *)malloc(dataSize);
    if (!pcmData) {
        printf("Could not allocate memory for pcm buffer\n");
        return NULL;
    }

    memcpy(pcmData, wavData + headerSize + 8, dataSize);
    
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


