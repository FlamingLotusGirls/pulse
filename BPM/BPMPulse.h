
#ifndef _BPMPulse_H_
#define _BPMPulse_H_

#ifdef __cplusplus__
extern "C" {
#endif

#include <stdint.h> // unit16_t, etc.
#include <netinet/in.h> // struct sockaddr_in

struct __BPMPulseData_t {

 uint8_t  pod_id; // which pod. pass as param in startup file.

 uint8_t  rolling_sequence;
	// just repeat every 256 iterations. for tracking gaps in
	// UDP packets in case we have some situation where it happens.

 uint16_t beat_interval_ms;
		// min BPM 30 has ms interval of 2000
		// max BPM 200 has ms interval of 300

 uint32_t elapsed_ms; // how long before now did this happen?

 float est_BPM; // computed as 60*1000/beat_interval_ms

 uint32_t local_time; // taken from time() call.
 
}__attribute__((packed)); 

typedef struct __BPMPulseData_t BPMPulseData_t;

extern int
SetupAnnounce_udp(char* ip, short port, int* sock, struct sockaddr_in* si_toserver);

extern void
AnnounceBPMdata_udp(double interval_ms, double elapsed_ms, uint8_t pod_id, uint8_t sequence, int sock, struct sockaddr_in* si);

#ifdef __cplusplus__
} // extern "C"
#endif

#endif // _BPMPulse_H_

