#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <stdlib.h>

#include "pcm_sound.h"

//#define BROADCAST_ADDR "255.255.255.255"
#define BROADCAST_ADDR "192.168.1.255"
#define ALL_RECEIVERS 255
#define HEARTBEAT_SOURCE 1
#define COMMAND_PORT 5001
#define HB_PORT 5000

#ifndef MAX
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#endif // MAX
#ifndef MIN
#define MIN(a,b) ((a) < (b) ? (a) : (b))
#endif // MIN


/*
typedef unsigned char uint8_t;
typedef unsigned long uint32_t;
typedef unsigned short uint16_t;
*/

struct __BPMPulseData_t {
    uint8_t  pod_id; // which pod. pass as param in startup file.

    uint8_t  rolling_sequence;
    // just repeat every 256 iterations. for tracking gaps in
    // UDP packets in case we have some situation where it happens.

    uint16_t beat_interval_ms;
    // min BPM 30 has ms interval of 2000
    // max BPM 200 has ms interval of 300

    uint32_t elapsed_ms; // how long before now did this happen?
    
    uint32_t timestamp;  // timestamp, normalized to the pod that sent this. Do not assume that the pods are in sync.

    float est_BPM; // computed as 60*1000/beat_interval_ms by sender.
 
}__attribute__((packed)); 

typedef struct __BPMPulseData_t BPMPulseData_t;

typedef struct __attribute((packed)) {
    uint8_t  receiver_id;         // which unit is this command for. 255 means 'this is for everyone'
    uint8_t  command_tracking_id; // id specific to this command, can be used for ACK/NACK if we build that 
    uint16_t command_id;          // command for the unit; do not respond to commands that you don't understand
    uint32_t command_data;        // may or may not have anything in it, depending on the command
} PulseCommand_t;

static uint8_t myId = 0; // Now read from command line. Caller reads config.
static uint8_t hbSource;
static int hbSocket;
static int cmdSocket; 
static int verbose = 0; // verbosity level.

static int initBroadcastSocketListener(unsigned short port);
static void pulseAudioListen();

static void Help() {
 fprintf(stderr, "sound_test: -ipod_id\n");
}
static void Usage() {
 Help(); exit(1);
}

void
GetOpts(int argc, char* argv[], uint8_t* pod_id)
{
	int i;
	for (i = 1; i < argc; i++) {

		if (argv[i][0]=='-') {
			switch(argv[i][1]) {
			case 'h': Help();
			break;
			case 'i': *pod_id = atoi(argv[i]+2);
			break;
			case 'v': verbose++;
			break;
			default: fprintf(stderr, "unknown option '%c'\n", argv[i][1]);
				Usage();
			}
		} else {
			fprintf(stderr, "what option ???\n");
			Usage();
		}
	}
}


int main(int argc, char **argv)
{
    GetOpts(argc, argv, &myId);

    if (pcmPlaybackInit() < 0) {
        printf("Failure to initialize sound system, aborting\n");
        return -1;
    }

    /*
    pcmPlayHeartBeat(60);
    sleep(5*60);
    pcmPlaybackStop();
    */
    
    // XXX TODO - read myId from config file
    hbSource = myId;
    
    hbSocket = initBroadcastSocketListener(HB_PORT);
    if (hbSocket < 0) {
        printf("Could not creating hb socket listener (error %d), aborting\n", hbSocket);
        return -1;
    }
 
    cmdSocket = initBroadcastSocketListener(COMMAND_PORT);
    if (cmdSocket < 0) {
        printf("Could not creating command socket listener (error %d), aborting\n", cmdSocket);
        return -1;
    }
    
    pulseAudioListen();
    return 0;
}



static int initBroadcastSocketListener(unsigned short port)
{
    int sockfd = 0;
    int rv;
    int optval = 1;
    struct sockaddr_in addr;

    if ((rv = socket(AF_INET, SOCK_DGRAM, 0)) <= 0) {
        return rv;
    }
    sockfd = rv;

    if ((rv = setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof optval)) != 0) {
        printf("setsocketopt returns %d, %s\n", rv, strerror(errno));
        return rv;
    }
    
/*
    if ((rv = setsockopt(sockfd, SOL_SOCKET, SO_BROADCAST, &optval, sizeof optval)) != 0) {
        printf("setsocketopt returns %d, %s\n", rv, strerror(errno));
        return rv;
    }
*/
    
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_port        = htons(port);
    addr.sin_addr.s_addr = inet_addr(BROADCAST_ADDR); /* INADDR_ANY; */
    
//    printf("Broadcast addr is 0x%x\n", inet_addr(BROADCAST_ADDR));
    
    if ((rv = bind(sockfd, (const struct sockaddr *)&addr, sizeof(addr))) < 0) {
        printf("bind returns %s\n", strerror(errno));
        return -EINVAL;
    }

    return sockfd;
}

static void pulseAudioListen()
{
    struct timeval timeout;
    int rv;
    int nfds = MAX(cmdSocket, hbSocket) + 1;
    
    fd_set read_fds, except_fds;
    printf("Command socket is %d\n", cmdSocket);
    printf("Heartbeat socket is %d\n", hbSocket);
    printf("nfds is %d\n", nfds);
    pcmPlayBreathing(0,128);
    //pcmPlaySpecial(SOUND_KABOOM, 128);
    pcmPlayHeartBeat(60, 128);
    while(1) {
        FD_ZERO(&read_fds);
        FD_ZERO(&except_fds);
        FD_SET(cmdSocket, &read_fds  );
        FD_SET(cmdSocket, &except_fds);
        FD_SET(hbSocket, &read_fds);
        FD_SET(hbSocket, &except_fds);
    
        // come up for air every second
        timeout.tv_sec  = 2;
        timeout.tv_usec = 0;
        
        // wait for timeout, or event on a socket...
        rv = select(nfds, &read_fds, NULL, &except_fds, &timeout);
        
//        printf("After select, rv is %d\n", rv);
        
        if (rv == 0) {
            printf("listen timeout... all is well...\n");  // leaving this in because Dave likes it
            continue; // timeout, nothing to do.
        }
        
        if (rv < 0) {
            printf("Select returns error %d, %s\n", errno, strerror(errno));
            continue;
        }
        
        if (rv > 0) {
            printf("Select returns event\n");
        }
        
        if (FD_ISSET(cmdSocket, &read_fds)) {
            // receive command datagram
            PulseCommand_t command;
            int numBytesRead = recv(cmdSocket, &command, sizeof(command), 0);
            if (numBytesRead < 0) {
                printf("Command socket: recv returns error %d, %s\n", numBytesRead,strerror(numBytesRead));
            } else if (numBytesRead < sizeof(command)) {
                printf("WARNING: Command socket: Receiving fewer bytes than expected, ignoring\n"); // Do we want/need to do anything with this?
            } else {
                printf("Received data on command socket\n");
                // a real live command to parse!
                if (command.receiver_id == myId || command.receiver_id == ALL_RECEIVERS) {
                    if (command.command_id == HEARTBEAT_SOURCE) {
                        hbSource = (uint8_t)(command.command_data);
                    } else {
                        // Don't currently know any other commands. Do nothing ... yet...
                    }
                }
            }
        }

        if (FD_ISSET(hbSocket, &read_fds)) {
            // receive hb datagram
            BPMPulseData_t hbData;
            int numBytesRead = recv(hbSocket, &hbData, sizeof(hbData), 0);
            if (numBytesRead < 0) {
                printf("HB socket: recv returns error %d, %s\n", numBytesRead, strerror(numBytesRead));
            } else if (numBytesRead < sizeof(hbData)) {
                printf("WARNING: HB socket: Receiving fewer bytes than expected, ignoring\n"); // Do we want/need to do anything with this?
            } else {
                // a real, live heartbeat!
                printf("Received data on hb socket, id is %d\n", hbData.pod_id);
                if (hbData.pod_id == hbSource) {
                    uint32_t hbRate = hbData.est_BPM; // yes, I am rounding here.
                    if (hbRate < 30 || hbRate > 200) { 
                        printf("Heartbeat rate %d is out of bounds\n", hbRate);
			hbRate = MAX(hbRate,30);
			hbRate = MIN(hbRate,200);
                    } else {
                        printf("received heart beat at %d\n", hbRate);
                    }
                    pcmPlayHeartBeat(hbRate, 128);
                }
            }
        } 
        
        if (FD_ISSET(cmdSocket, &except_fds)) {
            printf("exception on cmd socket\n");
            // XXX not exactly sure what sort of exceptions we might see here. Leaving blank for now.
        }
        
        if (FD_ISSET(hbSocket, &except_fds)) {
            printf("exception on hb socket\n");
            // XXX not exactly sure what sort of exceptions we might see here. Leaving blank for now.
        }
    }
}
