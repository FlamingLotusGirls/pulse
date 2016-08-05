//
// The client is sending messages to the 'server'.
// In this case, 'server' just means a known ip and port,
// but we are giving the server data, not vice-versa.
//

#include <arpa/inet.h>
//#include <netinet/in.h>
#include <stdio.h>
#include <time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>

#include <stdlib.h> // exit() on some platforms.
#include <string.h> // memset() on some platforms.

#include "BPMPulse.h"

int
SetupAnnounce_udp(char* ip, short port, int* sock, struct sockaddr_in* si_toserver)
{
	int opton=1;
	if ((*sock=socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP))==-1) {
		//Fatal("Can't create socket\n");
		return -1;
	}
	// are sockets on raspbian set O_NONBLOCK by default?
	int arg;
	int flags = fcntl(*sock, F_GETFL, arg);
	flags &= ~ O_NONBLOCK;
	fcntl(*sock, F_SETFL, flags);

	setsockopt(*sock, SOL_SOCKET, SO_REUSEADDR, &opton, sizeof(opton));
	setsockopt(*sock, SOL_SOCKET, SO_BROADCAST, &opton, sizeof(opton));

	memset((char *)si_toserver, 0, sizeof(*si_toserver));
	si_toserver->sin_family = AF_INET;
	si_toserver->sin_port = htons(port);

	if (inet_aton(ip, &(si_toserver->sin_addr))==0) {
		//Fatal("inet_aton() failed\n");
		return -2;
	}

	return 0; // good.
}

//
// pass in the beat period in milliseconds, also the elapsed time
// in milliseconds from the most recent heart beat to now.
//
void
AnnounceBPMdata_udp(double interval_ms, double elapsed_ms, uint8_t pod_id, uint8_t sequence, int sock, struct sockaddr_in* si) {

	BPMPulseData_t data;
	int ret;

	data.beat_interval_ms = interval_ms;
	data.elapsed_ms = elapsed_ms;
	data.pod_id = pod_id;
	data.rolling_sequence = sequence;
	data.est_BPM = (interval_ms>0)? 60.*1000./interval_ms : 0;
	data.local_time = time(NULL);

	ret = sendto(sock, (char*)&data, sizeof(data), 0, (struct sockaddr*)si, sizeof(struct sockaddr_in));

	if (ret != 0) { printf("OUCH! sendto() errno %d (%s)\n", errno, strerror(errno)); }
}

#ifdef UNIT_TEST
int main(int ac, char* av[]) {

	char* srv_ip = "127.0.0.1";
	short port = 1234;
	int errors = 0;
	int verbose = 0;

	if (ac > 1) srv_ip = av[1];
	if (ac > 2) port = atoi(av[2]);

	struct sockaddr_in si_toserver;
	int s, i;

	//socklen_t slen;
	//int slen; // change for your platform.


	if (SetupAnnounce_udp(&s,&si_toserver) != 0) {
		printf("Can't setup udp socket\n");
		exit(1);
	}
	TestServer(s, &si_toserver);

	close(s);
	return 0;
}
#endif // UNIT_TEST

