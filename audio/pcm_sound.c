/* And now some C code for handling the audio 
 */

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <mqueue.h>
#include <poll.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <asoundlib.h>

#include "pcm_config.h"
#include "pcm_utils.h"


#define REQUESTED_FRAME_RATE 44100
//#define REQUESTED_BUFFER_SIZE_US 500000
#define REQUESTED_BUFFER_SIZE_US 100000
//#define REQUESTED_PERIOD_SIZE_US 100000
#define PERIODS_PER_BUFFER 4
//#define REQUESTED_PERIOD_SIZE_US  20000

// NB - sounds are assumed to be mono 

static unsigned char *m_currentSoundBuf    = NULL;  // sound we're currently playing. 
static unsigned char *m_currentSoundBufPtr = NULL;  // pointer to current data in the current sound buffer
static unsigned char *m_nextSoundBuf       = NULL;  // Next sound to play
static int  m_currentSoundLength           = 0;     // length of current sound, in frames
static int  m_nextSoundLength              = 0;     // length of next sound, in frames
static int  m_nextSoundTimeFrames          = 0;     // how many frames away from the current write pointer to start the next sound

//static unsigned char *lastSoundBuf       = NULL;   // last sound we played, in case we have to re-play it
//static int lastSoundLength          = 0;
static int m_lastSoundFreqFrames      = 0;

static pthread_t playbackThread;

static unsigned char *silentBuffer        = NULL;    // Buffer, pre-filled with silence, that we can pull from

static const char *device = "default";    // hope this works.... XXX
static snd_pcm_t *handle    = NULL;
static snd_output_t *output = NULL;

static snd_pcm_uframes_t  m_bufferSize_frames = 0;
static snd_pcm_uframes_t  m_periodSize_frames = 0; 

static int m_bytesPerSample = 2; 
static int m_nChannels      = 1;
static unsigned int m_frameRate      = REQUESTED_FRAME_RATE; 

static mqd_t commandmq;

// XXX for the moment just to fix compliation errors
//const char *snd_strerror(int err);

// Okay. It appears that we do select to receive events. So I do need
// a sound processing thread, and I'm going to select on buffer starve events
// as well as commands from an incoming message queue.

#define HB_FREQ_MIN 30
#define HB_FREQ_MAX 150

typedef struct {
    unsigned char *soundBuf;
    int bufLen;
    struct timespec startTime;
    int freqMs;
}PcmSound;


// initialization
static void createPcmSound(PcmSound *sound, unsigned char *pcmSoundBuf, int pcmBufLen, int freqMs); 
static int setPcmParams(snd_pcm_t *handle, snd_pcm_hw_params_t *hwParams, snd_pcm_sw_params_t *swParams); 
static int setHwParams(snd_pcm_t *handle, snd_pcm_hw_params_t *hwParams);
static int setSwParams(snd_pcm_t *handle, snd_pcm_sw_params_t *swParams);

// playback thread
static void* pcmPlaybackThread(void *arg);
static int feedBuffer(void); 
static snd_pcm_sframes_t getAudioDelay(void);
static int initializeSilentBuffer(int silentTimeMs); 
static int fillBufferWithSilence(int silentBytes, int *reInit); 
static int fillBufferWithSound(unsigned char *soundBuffer, int soundBytes, int *reInit);
static int xrun_recovery(snd_pcm_t *handle, int err);


int pcmPlaySound(unsigned char* pcmSoundBuf, int pcmBufLen, unsigned int freqMs)
{
    PcmSound newSound; 
    createPcmSound(&newSound, pcmSoundBuf, pcmBufLen, freqMs);
    if (mq_send(commandmq, (const char *)&newSound, sizeof(newSound), 0) != 0) {
        printf("Could not send message to play sound: %s\n", strerror(errno));
        return ERR_PCM_MISC;
    }
    
    return 0;
}

void pcmPlayHeartBeat(unsigned int freqBPS)
{
    HbData *sound;
    
    if (freqBPS > HB_FREQ_MAX) {
        freqBPS = HB_FREQ_MAX;
    } else if (freqBPS < HB_FREQ_MIN) {
        freqBPS = HB_FREQ_MIN;
    }
    
    // Get sound appropriate for this frequency
    sound = PcmConfig_getHbSound(freqBPS);
    if (sound) {
        pcmPlaySound(sound->data, sound->datalen, 1000*60/freqBPS);
    } else {
        printf("No heartbeat sound to play\n");
    }
}



int pcmPlaybackInit() 
{
    int err;
    pthread_attr_t attr;
    
    if ((err = PcmConfig_Read()) != 0){
        return err;
    }
    
    if ((err = initializeSilentBuffer(10000)) != 0) {
        return err;
    }
    
    snd_pcm_hw_params_t *hwParams = NULL;
    snd_pcm_sw_params_t *swParams = NULL;
    snd_pcm_hw_params_alloca(&hwParams);
    snd_pcm_sw_params_alloca(&swParams);
    
    if (hwParams == NULL || swParams == NULL) {
        printf("Could not allocate parameter buffers\n");
        return ERR_PCM_MISC;
    }
        
    if ((err = snd_output_stdio_attach(&output, stdout, 0)) < 0) {
        printf("Output failed: %s\n", snd_strerror(err)); 
        return ERR_PCM_MISC;
    }

    if ((err = snd_pcm_open(&handle, device, SND_PCM_STREAM_PLAYBACK, 0)) < 0) {
        printf("Playback open error: %s\n", snd_strerror(err));
        return ERR_PCM_OPEN; 
    }
    
    if ((err = setPcmParams(handle, hwParams, swParams)) < 0) {
        printf("Set parameter error: %s\n", snd_strerror(err));
        return ERR_PCM_PARAM;
    }
    
    struct mq_attr attrs;
    memset(&attrs, 0, sizeof(attrs));
    attrs.mq_flags = 0;
    attrs.mq_maxmsg = 10;
    attrs.mq_msgsize = sizeof(PcmSound);
    
    printf("creating message queue with attrs!\n");
    
//    mq_unlink("/Pulse_PCM_MQ");

    if ((commandmq = mq_open("/Pulse_PCM_MQ", O_RDWR|O_CREAT, S_IRWXU | S_IRWXG, &attrs)) < 0) { 
        printf("Error creating message queue: %s\n", strerror(errno));
        return ERR_PCM_QUEUE;
    }
        
    if ((err = pthread_attr_init(&attr)) != 0) {
        printf("Error initializing thread: %s\n", strerror(err));
        return ERR_PCM_MISC;   
    }    
    
    if ((err = pthread_create(&playbackThread, &attr, &pcmPlaybackThread, NULL)) != 0) {
        printf("Error creating playback thread: %s\n", strerror(err));
        return ERR_PCM_THREAD_CREATE;
    } 
    
    pthread_attr_destroy(&attr); 

    
    return 0;
}


static void createPcmSound(PcmSound *sound, unsigned char *pcmSoundBuf, int pcmBufLen, int freqMs) 
{
    if (sound) {
        sound->soundBuf = pcmSoundBuf;
        sound->bufLen   = pcmBufLen;
        struct timespec currentTime;
        clock_gettime(CLOCK_MONOTONIC, &currentTime);
        
        int playbackStartDeltaS  = freqMs/1000;
        int playbackStartMs = freqMs - (playbackStartDeltaS * 1000);
        int playbackStartNs = currentTime.tv_nsec + (playbackStartMs * 1000000);
        if (playbackStartNs < currentTime.tv_nsec) {  // do we ever actually wrap? check the resolution
            printf("create pcm sound wraps!");
            // XXX check can wrap happen
        } else if (playbackStartNs > 1000000000) {
            printf("adding a second, subtracting ns\n");
            playbackStartDeltaS++;
            playbackStartNs -= 1000000000;
        }
        
        sound->startTime.tv_sec  = currentTime.tv_sec + playbackStartDeltaS;
        sound->startTime.tv_nsec = playbackStartNs;
        sound->freqMs = freqMs;
    }
    
    return;
}


// XXX must have shorter periods in order to handle higher heart rates


static int setPcmParams(snd_pcm_t *handle, snd_pcm_hw_params_t *hwParams, snd_pcm_sw_params_t *swParams) 
{
    int err = 0;
    if ((err = setHwParams(handle, hwParams)) < 0) {
        return err;
    }
        
    if ((err = setSwParams(handle, swParams)) < 0) {
        return err;
    }
    
    return 0;
}

static int setHwParams(snd_pcm_t *handle, snd_pcm_hw_params_t *hwParams) {

    int err, dir;
    
    // set hardware parameters first...
    if ((err = snd_pcm_hw_params_any(handle, hwParams)) < 0) {
        printf("No playback configurations available: %s\n", snd_strerror(err));
        return err;
    }

    if ((err = snd_pcm_hw_params_set_rate_resample(handle, hwParams, 1)) < 0) {
        printf("No playback configurations available: %s\n", snd_strerror(err));
        return err;
    }

    if ((err = snd_pcm_hw_params_set_access(handle, hwParams, SND_PCM_ACCESS_RW_INTERLEAVED)) < 0) {
//    if ((err = snd_pcm_hw_params_set_access(handle, hwParams, SND_PCM_ACCESS_RW_NONINTERLEAVED)) < 0) {
        printf("Could not set raw interleaved access: %s\n", snd_strerror(err));
        return err;
    }

//    if ((err = snd_pcm_hw_params_set_format(handle, hwParams, SND_PCM_FORMAT_U8 )) < 0) {
    if ((err = snd_pcm_hw_params_set_format(handle, hwParams, SND_PCM_FORMAT_S16_LE )) < 0) {
        printf("Could not sent sound format to 16bit: %s\n", snd_strerror(err));
        return err;
    }

    if ((err = snd_pcm_hw_params_set_channels(handle, hwParams, 1)) < 0) {
        printf("Could not set mono mode: %s\n", snd_strerror(err));
        return err;
    }
    
    if ((err = snd_pcm_hw_params_set_rate_near(handle, hwParams, &m_frameRate, 0)) < 0) {
        printf("Could not set rate: %s\n", snd_strerror(err));
        return err;
    }
    if (m_frameRate != REQUESTED_FRAME_RATE) {
        printf("Sample Rate %d not equal to requested rate %d\n", m_frameRate, REQUESTED_FRAME_RATE);
    }
    
    
    printf("Init: Frame rate is %d\n", m_frameRate);
    unsigned int requestedBufferSize = (REQUESTED_BUFFER_SIZE_US) * (REQUESTED_FRAME_RATE/10)/100000;
    // and let's 
    // and let's make sure it is divisible by our period size
    snd_pcm_uframes_t requestedPeriodSize = requestedBufferSize/PERIODS_PER_BUFFER;
        
        
    printf("Init: Requested period size is %d frames\n", (int) requestedPeriodSize);
    if ((err = snd_pcm_hw_params_set_period_size_near(handle, hwParams, &requestedPeriodSize, NULL)) < 0) {
        printf("Could not set period size: %s\n", snd_strerror(err));
        return err;
    }
    
    printf("Init: Actual period size is %d frames\n", (int)requestedPeriodSize);
    
    if ((err = snd_pcm_hw_params_get_period_size(hwParams, &m_periodSize_frames, &dir)) < 0) {
        printf("Could not get period size: %s\n", snd_strerror(err));
        return err;
    }
    printf("Init: Actual period size (again) is %d frames\n", (int)m_periodSize_frames);
    
    requestedBufferSize = m_periodSize_frames * PERIODS_PER_BUFFER;
    
    printf("Init: Requested buffer size is %d frames\n", requestedBufferSize);  // buffer size in frames
    if ((err = snd_pcm_hw_params_set_buffer_size(handle, hwParams, requestedBufferSize)) < 0) {
        printf("Could not set buffer size: %s\n", snd_strerror(err));
        return err;
    }
    if ((err = snd_pcm_hw_params_get_buffer_size(hwParams, &m_bufferSize_frames)) < 0) {
        printf("Could not get buffer size: %s\n", snd_strerror(err));
        return err;
    }
    printf("Init: actual buffer size is %d frames\n", (int)m_bufferSize_frames);
    // XXX TODO - since we're now using 16 bit samples, I have to care about endianness
    // Fortunately, since WAV files appear to be little endian and this processor is little-endian,
    // all should be well. But.
    
    if (m_bufferSize_frames != requestedBufferSize) {
        if (m_bufferSize_frames % PERIODS_PER_BUFFER != 0) {
            printf("Cannot create buffer at specified size with the desired number of periods.\n Change parameters and recompile\n");
            return -1;
        }
        requestedPeriodSize = m_bufferSize_frames/PERIODS_PER_BUFFER;
    }

    if (m_bufferSize_frames % m_periodSize_frames != 0) {
        printf("Buffer size could not be made an integral multiple of period size. Aborting\n");
        return -1;
    }

    
    if ((err = snd_pcm_hw_params(handle, hwParams)) < 0) {
        printf("Cannot commit hw params: %s\n", snd_strerror(err));
        return err;
    }
    
    return 0;
}

static int setSwParams(snd_pcm_t *handle, snd_pcm_sw_params_t *swParams)
{
    int err;
    if ((err = snd_pcm_sw_params_current(handle, swParams)) < 0) {
        printf("Cannot determine current swParams: %s\n", snd_strerror(err));
        return err;
    }
    /* start the transfer when the buffer is almost full: */
    /* (buffer_size / avail_min) * avail_min */
    int nPeriods = m_bufferSize_frames/m_periodSize_frames;
    if (nPeriods > 1) nPeriods++;
    // set start threshhold to just start immediatrly
    if ((err = snd_pcm_sw_params_set_start_threshold(handle, swParams,  0U)) < 0) {
        printf("Unable to set start threshold mode for playback: %s\n", snd_strerror(err));
        return err;
    }
    /* allow the transfer when at least periodSize samples can be processed */
    /* or disable this mechanism when period event is enabled (aka interrupt like style processing) */
    if ((err = snd_pcm_sw_params_set_avail_min(handle, swParams, m_periodSize_frames )) < 0) {
        printf("Unable to set avail min for playback: %s\n", snd_strerror(err));
        return err;
    }

    /* write the parameters to the playback device */
    if ((err = snd_pcm_sw_params(handle, swParams)) < 0) {
        printf("Unable to set sw params for playback: %s\n", snd_strerror(err));
        return err;
    }
    return 0;
}


/* Everything from here down should only be called on the playback thread */
static void* pcmPlaybackThread(void *arg)
{
    struct pollfd *ufds;
    PcmSound soundMsg;
    int err;
    
    int pcmDescriptorsCount = snd_pcm_poll_descriptors_count (handle);
    if (pcmDescriptorsCount <= 0) {
        printf("PCM Playback Fatal: Invalid number of poll descriptors\n");
        return NULL;
    }
    printf("Have %d descriptors\n", pcmDescriptorsCount);
    ufds = malloc(sizeof(struct pollfd) * (pcmDescriptorsCount + 1));
    if (!ufds) {
        printf("PCM Playback Fatal: Could not allocate memory for poll descriptors \n");
        return NULL;
    }
    
    // setting up the message queue fd structure first
    ufds->fd = commandmq;
    ufds->events = POLLIN;
    ufds->revents = 0;
    
    // now the sound events
    if ((err = snd_pcm_poll_descriptors(handle, ufds+1, pcmDescriptorsCount)) < 0) {
        printf("Unable to obtain poll descriptors for playback: %s\n", snd_strerror(err));
        return NULL;
    }
    /*
    printf("Open state is %d\n", SND_PCM_STATE_OPEN);
    printf("Setup state is %d\n", SND_PCM_STATE_SETUP);
    printf("Prepared state is %d\n", SND_PCM_STATE_PREPARED);
    printf("Running state is %d\n", SND_PCM_STATE_RUNNING);
    printf("Xrun state is %d\n", SND_PCM_STATE_XRUN);
    printf("Draining state is %d\n", SND_PCM_STATE_DRAINING);
    printf("Paused state is %d\n", SND_PCM_STATE_PAUSED);
    printf("Suspended state is %d\n", SND_PCM_STATE_SUSPENDED);
    printf("Disconnected state is %d\n", SND_PCM_STATE_DISCONNECTED);
    */
    while (1) {
//        int snd_state = snd_pcm_state(handle);
//        printf("LOOP START: Sound state is %d\n", snd_state);
//        if (snd_pcm_state(handle) == SND_PCM_STATE_RUNNING) {
            struct timespec pollStartTime;
            clock_gettime(CLOCK_MONOTONIC, &pollStartTime);
            err = poll(ufds, pcmDescriptorsCount + 1, -1);
            if (err == 0) { // this shouldn't happen
                printf("Unexpected timeout on poll\n");
            } else if (err < 0) { // actual error. Maybe bail
                printf("Warning: Poll() returns error %s\n", strerror(errno));
                // XXX check for error and decide what to do...
                // XXX set waittime...
            } else {
                // check fds for results
                unsigned short mqEvent = ufds[0].revents;
                if (mqEvent) {
//                    printf("Receive poll event %d on message queue\n", mqEvent);
                    if (mqEvent & POLLIN) {
                        struct mq_attr attr;
                        mq_getattr(commandmq, &attr);
//                        printf("sound message message size is %ld, buffer size is %d\n", attr.mq_msgsize, sizeof(soundMsg));
                        int bytesRead = mq_receive(commandmq, (char *)(&soundMsg), sizeof(soundMsg), NULL);
//                        printf("Read %d bytes from message queue\n", bytesRead);
                        if (bytesRead == -1) {
                            printf("Warning: Message queue returns error, %s\n", strerror(errno));
                        } else if (bytesRead < sizeof(soundMsg)) {
                            printf("Received malformed sound message, %d bytes, discarding\n", bytesRead);
                        } else {
                            struct timespec currentTime;
                            clock_gettime(CLOCK_MONOTONIC, &currentTime);
                            if ((currentTime.tv_sec > soundMsg.startTime.tv_sec) || 
                                 ( (currentTime.tv_sec == soundMsg.startTime.tv_sec) && 
                                   (currentTime.tv_nsec > soundMsg.startTime.tv_nsec))) {
                                // This message has expired. Ignore it. 
                                printf("Received expired message, ignoring\n");  
                            } else {
                                printf("SOUND MESSAGE RECEIVED\n");
                                m_nextSoundBuf    = soundMsg.soundBuf;
                                m_nextSoundLength = soundMsg.bufLen/(m_nChannels * m_bytesPerSample); // get length in frames
                                printf("Sound is %d frames (%d bytes)\n", m_nextSoundLength, soundMsg.bufLen);
                                
                                struct timespec nextTime;
                                nextTime.tv_sec  = soundMsg.startTime.tv_sec;
                                nextTime.tv_nsec = soundMsg.startTime.tv_nsec;
                                int deltaS = nextTime.tv_sec - currentTime.tv_sec;
                                if (nextTime.tv_nsec < currentTime.tv_nsec) {
                                    deltaS -= 1;
                                    nextTime.tv_nsec += 1000000000;
                                }
                                int deltaNs = nextTime.tv_nsec - currentTime.tv_nsec;
                                int nextSoundDelayMs = (deltaS * 1000) +  deltaNs/1000000; // how long to wait to play the next sound
                                printf("Next sound delay (ms) is %d\n", nextSoundDelayMs);
                                int nextSoundDelayFrames = (nextSoundDelayMs * m_frameRate)/1000;
                                snd_pcm_sframes_t delayFrames = getAudioDelay();
                                int delayMs = delayFrames*1000/m_frameRate; // XXXX check this
                                printf("Audio buffer delay (ms) is %d\n", delayMs);
                                m_nextSoundTimeFrames = nextSoundDelayFrames - delayFrames;
                                m_nextSoundTimeFrames = MAX(0, m_nextSoundTimeFrames);
                                printf("NextSoundTimeFrames is %d\n", m_nextSoundTimeFrames);
                                printf("Wait time between sounds is %d\n", soundMsg.freqMs);
                                //lastSoundBuf    = m_nextSoundBuf;
                                //lastSoundLength     = m_nextSoundLength;
                                m_lastSoundFreqFrames = (soundMsg.freqMs * m_frameRate)/ 1000;
                            }
                        }
                    } 
                    ufds[0].revents = 0;
                } else {
                    unsigned short revents;
                    snd_pcm_poll_descriptors_revents(handle, ufds+1, pcmDescriptorsCount, &revents);
                    if (revents & POLLERR) {
                        printf("Warning: PCM poll returns IO error\n");
                        if (snd_pcm_state(handle) == SND_PCM_STATE_XRUN ||
                            snd_pcm_state(handle) == SND_PCM_STATE_SUSPENDED) {
                            err = snd_pcm_state(handle) == SND_PCM_STATE_XRUN ? -EPIPE : -ESTRPIPE;
                            printf("PCM state is %d\n", snd_pcm_state(handle));
                            if (xrun_recovery(handle, err) < 0) {
                                printf("Cannot recover from error %s\n", snd_strerror(err));
                                exit(EXIT_FAILURE);// XXX not what I want...
                            }
                        }
                    }
                    if (revents & POLLOUT) {
                        printf("!!Sound system requires feeding\n");
                        feedBuffer();
                    }
                }
            }
//        }
    }
    return NULL;
        
}

// write one period to the buffer
static int feedBuffer(void) {
    int reInit = 0;
    int totalFramesFilled = 0;
    int bytesPerFrame = m_nChannels * m_bytesPerSample;
    
    // if we're currently playing a sound, attempt to finish it
    if (m_currentSoundBuf) {
        assert(m_currentSoundBufPtr);
        int framesToWrite = MIN(m_currentSoundLength - ((m_currentSoundBufPtr - m_currentSoundBuf))/bytesPerFrame, m_periodSize_frames);
//        printf("WRITE SOUND DATA 1\n");
        int framesFilled = fillBufferWithSound(m_currentSoundBufPtr, framesToWrite, &reInit);
        printf("Wrote %d frames\n", framesFilled);
        if (framesFilled >= 0) {
//            printf("Wrote %d frames to sound buffer\n", framesFilled);
            totalFramesFilled    += framesFilled;
            m_currentSoundBufPtr += framesFilled * bytesPerFrame;
            if (m_currentSoundBufPtr - m_currentSoundBuf >= m_currentSoundLength * bytesPerFrame) {  
                // we've finished the current sound. Reset variables. 
                // But first, set the next sound if there isn't one already
                printf("!!!! Finished current sound\n");
                if (!m_nextSoundBuf) {  // Auto fill the next sound, if there is no queue'd one
                    m_nextSoundBuf        = m_currentSoundBuf; 
                    m_nextSoundLength     = m_currentSoundLength;
                    m_nextSoundTimeFrames = m_lastSoundFreqFrames - m_currentSoundLength + totalFramesFilled; // NB - at this point, nextSoundTime is supposed to be offset from the beginning of the period. That's why we add totalFramesFilled
                    if (m_nextSoundTimeFrames <=0 ){
                        printf("!!!! Maximum beat frequency for this sound!\n");
                        m_nextSoundTimeFrames = 0;
                    }
                    printf("Auto filling next sound, m_nextSoundtimeFrames is %d\n", m_nextSoundTimeFrames);
                }
                m_currentSoundBuf    = NULL;
                m_currentSoundBufPtr = NULL;
                m_currentSoundLength = 0;
            }
            if (framesFilled != framesToWrite) {
                printf("Primary write: Did not write as many frames as expected: %d written, vs %d expected\n", framesFilled, framesToWrite);
                if (reInit) {
                    if (m_nextSoundBuf) {
                        m_nextSoundTimeFrames = MAX(0, m_nextSoundTimeFrames - framesFilled);
                    }
                    return -1;
                }
            }
        } else {
            // This is an unrecoverable error. Not sure what to do.
            printf("Audio system unrecoverable error. Ack Ack Ack\n"); // XXX FIXME
        }   
    }
        
    // if there's space in the buffer, add more stuff
    // silence and then the next sound, if there is a next sound.
    if (totalFramesFilled < m_periodSize_frames) {
        assert(!m_currentSoundBuf); 
        int framesFilled = 0;
        int framesToWrite = 0;
        if (!m_nextSoundBuf) {
            // no next sound - fill the rest of the thing with silence...
            framesToWrite = m_periodSize_frames - totalFramesFilled;
//            printf("Silence fill 1\n");
            framesFilled = fillBufferWithSilence(framesToWrite, &reInit);
        } else if (m_nextSoundTimeFrames > totalFramesFilled) {
            // if next sound starts after the end of what we've got, fill the bits between
            // with silence.
            framesToWrite = MIN(m_periodSize_frames-totalFramesFilled, m_nextSoundTimeFrames - totalFramesFilled);
            printf("Silence fill 2\n");
            framesFilled = fillBufferWithSilence(framesToWrite, &reInit);
        } else {
            printf("!!!CSW!!! No silence - maximum heartbeat with this sound?\n");
        }
        if (framesFilled >= 0) {
            totalFramesFilled += framesFilled;
            if (framesFilled != framesToWrite) {
                printf("Fill silence: Did not write as many bytes as expected: %d written, vs %d expected\n", framesFilled, framesToWrite);
                if (reInit) {
                    if (m_nextSoundBuf) {
                        m_nextSoundTimeFrames = MAX(0, m_nextSoundTimeFrames - framesFilled);
                    }
                    return -1;
                } 
            }
        } else {
            // This is an unrecoverable error. Not sure what to do.
            printf("Audio system unrecoverable error. Ack Ack Ack\n"); // XXX FIXME
        }
        
        // Next sound, if there's space for it
        if (totalFramesFilled < m_periodSize_frames) {
            assert(m_nextSoundBuf);
            m_currentSoundBuf     = m_nextSoundBuf;
            m_currentSoundBufPtr  = m_currentSoundBuf;
            m_currentSoundLength  = m_nextSoundLength;
            m_nextSoundBuf        = NULL;
            m_nextSoundTimeFrames = 0;
            framesToWrite = MIN(m_currentSoundLength, m_periodSize_frames -totalFramesFilled);
//            printf("WRITE SOUND DATA 2\n");
            framesFilled = fillBufferWithSound(m_currentSoundBuf, framesToWrite, &reInit);
            printf("Wrote %d frames\n", framesFilled);
            if (framesFilled >= 0) {
                totalFramesFilled += framesFilled;
                if (m_currentSoundLength <= framesFilled) {
                    m_currentSoundBuf    = NULL;
                    m_currentSoundBufPtr = NULL;
                    m_currentSoundLength = 0;
                } else {
                    m_currentSoundBufPtr += framesFilled * bytesPerFrame;
                }
                if (framesFilled != framesToWrite) {
                    printf("2ndary Fill sound: Did not write as many frames as expected: %d written, vs %d expected\n", framesFilled, framesToWrite);
                    if (reInit) {
                        return -1;
                    } 
                } 
            } else {
                // This is an unrecoverable error. Not sure what to do.
                printf("Audio system unrecoverable error. Ack Ack Ack\n"); // XXX FIXME
            }
        }
        
        // And finally, silence, if there's space for it
        if (totalFramesFilled < m_periodSize_frames) {
            assert(!m_currentSoundBuf);
            assert(!m_nextSoundBuf);
            framesToWrite = totalFramesFilled < m_periodSize_frames;
            framesFilled = fillBufferWithSilence(framesToWrite, &reInit);
            if (framesFilled >= 0) {
                totalFramesFilled += framesFilled;
                if (framesFilled != framesToWrite) {
                    printf("Did not write as many frames as expected: %d written, vs %d expected\n", framesFilled, framesToWrite);
                    if (reInit) {
                        return -1;
                    } 
                }
            } else {
                // This is an unrecoverable error. Not sure what to do.
                printf("Audio system unrecoverable error. Ack Ack Ack\n"); // XXX FIXME
            }
        }
        
        // adjust nextSoundTimeBytes, if necessary
        if (m_nextSoundBuf) {
            m_nextSoundTimeFrames -= totalFramesFilled;
//            printf("nextSoundTimeFrames is %d\n", nextSoundTimeFrames);
        }
    }
    
    return 0;
}

static snd_pcm_sframes_t getAudioDelay(void)
{
    int err;
    snd_pcm_sframes_t delayFrames = -1;;
    snd_pcm_status_t *status;
    snd_pcm_status_alloca(&status);
    
    if ((err = snd_pcm_status(handle, status)) < 0) {
        printf("Error getting pcm audio status\n");
    } else {
        delayFrames = snd_pcm_status_get_delay(status);
    }
    
    printf("Audio delay is %ld frames\n", (long)delayFrames);
    return delayFrames;
}

static int initializeSilentBuffer(int silentTimeMs) 
{
    // get number of sample for silent time
    // bytes to frames, frames per second...
    int nSamples = (m_frameRate * m_nChannels * silentTimeMs)/1000;
    silentBuffer = (unsigned char *)malloc(nSamples * m_bytesPerSample);
    if (!silentBuffer) {
        return ERR_PCM_MEMORY;
    }
    snd_pcm_format_set_silence(SND_PCM_FORMAT_S16_LE, silentBuffer, nSamples);
    return 0;
}

static int fillBufferWithSilence(int silentFrames, int *reInit) 
{
//    printf("Writing some silence...\n");
    return fillBufferWithSound(silentBuffer, silentFrames, reInit);
}
 

static int fillBufferWithSound(unsigned char *soundBuffer, int nFramesToWrite, int *reInit)
{
    int nFramesWritten = 0;
    int err;
    
    if (reInit) {
        *reInit = 0;
    }

    while (nFramesToWrite > 0) {
        nFramesWritten = 0;
//        printf("writing %d frames\n", nFramesToWrite);
        err = snd_pcm_writei(handle, soundBuffer, nFramesToWrite);
        if (err < 0) {
            printf("Error writing to sound buffer, error is %s\n", strerror(err));
            if (xrun_recovery(handle, err) < 0) {
                return err;
            }
            if (reInit) {
                *reInit = 1;
            } 
            break;
        } else {
//            printf("Wrote %d frames\n", err);
            nFramesWritten = err;
        }
        nFramesToWrite -= nFramesWritten;
    }
    
    return nFramesWritten;
}

/*
 *   Underrun and suspend recovery
 */
 
static int verbose = 1;
static int xrun_recovery(snd_pcm_t *handle, int err)
{
    if (verbose)
        printf("stream recovery\n");
    if (err == -EPIPE) {    /* under-run */
        err = snd_pcm_prepare(handle);
        if (err < 0)
            printf("Can't recovery from underrun, prepare failed: %s\n", snd_strerror(err));
        return 0;
    } else if (err == -ESTRPIPE) {
        while ((err = snd_pcm_resume(handle)) == -EAGAIN)
            sleep(1);       /* wait until the suspend flag is released */
        if (err < 0) {
            err = snd_pcm_prepare(handle);
            if (err < 0)
                printf("Can't recovery from suspend, prepare failed: %s\n", snd_strerror(err));
        }
        return 0;
    }
    return err;
}



void pcmPlaybackStop() 
{
    snd_pcm_close(handle);
}




