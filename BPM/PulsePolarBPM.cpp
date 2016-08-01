/*********************************************************************************

PulsePolarBPM.cpp

Read samples from the Polar heart beat sensor.
Estimate the BPM and time (include time delay from detected pulse
along with bpm so the reader can estimate accurate phase).

This is partially based on GoIO_DeviceCheck.cpp which requires the copyright
below be present. BPM estimation and network code by Flaming Lotus Girls 2016.
Complain to dave0mi@gmail.com about bugs.

Copyright (c) 2010, Vernier Software & Technology
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Vernier Software & Technology nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL VERNIER SOFTWARE & TECHNOLOGY BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

**********************************************************************************/
// GoIO_DeviceCheck.cpp : Defines the entry point for the console application.
//


#define MEASUREMENT_PERIOD 0.020 // 20ms sampling - put at top easy to find ...


#include <stdio.h>
#include <string.h>
#include <memory.h>
#include <sys/time.h>
#include <stdlib.h>
#include <GoIO_DLL_interface.h>

// for Apple ...
#ifdef __MACH__
#include <mach/mach_time.h>
#define CLOCK_REALTIME 0
#define CLOCK_MONOTONIC_RAW 0
typedef clock_id_t clockid_t;
int clock_gettime(int clk_id, struct timespec *t){
    mach_timebase_info_data_t timebase;
    mach_timebase_info(&timebase);
    uint64_t time;
    time = mach_absolute_time();
    double nseconds = ((double)time * (double)timebase.numer)/((double)timebase.denom);
    double seconds = ((double)time * (double)timebase.numer)/((double)timebase.denom * 1e9);
    t->tv_sec = seconds;
    t->tv_nsec = nseconds;
    return 0;
}
#else
#include <time.h>
#endif

// udp support ...
#include "BPMPulse.h"

#ifndef GOIO_MAX_SIZE_DEVICE_NAME
#define GOIO_MAX_SIZE_DEVICE_NAME 128
#endif

static int verbose = 0;

const char *deviceDesc[8] = {"?", "?", "Go! Temp", "Go! Link", "Go! Motion", "?", "?", "Mini GC"};

bool GetAvailableDeviceName(char *deviceName, gtype_int32 nameLength, gtype_int32 *pVendorId, gtype_int32 *pProductId);
static void OSSleep(unsigned long msToSleep);


#define AVERAGING_PULSES 4 // number of pulse intervals before we compute
			  // a bpm. We can insist on a max std-dev too if we like ...
#define MAX_SEARCH_THRESHOLD 2.0 // don't look for maxima below this data value!

typedef struct {

 double currentBeatInterval_ms;
 int justGenerated; // flag to indicate that estimate was just estimated.

 int count,dtCount;        // count measurements.
 int consecutiveBeats; // consecutive legal beat intervals ...

 double prevVal;  // track previous measurement ...
 struct timespec prevTime;

 double prevMaxVal; // previous peak value ...
 struct timespec prevMaxTime;
 struct timespec prevBeatTime;

 // intervals between most recent pulses in ms.
 unsigned b_i_idx;
 unsigned beat_intervals_ms[AVERAGING_PULSES];

 int earlyMaxBooboo;

} bpm_det_state_t;

static clockid_t sWhich_clock = CLOCK_MONOTONIC_RAW;
static bpm_det_state_t bs;


unsigned
Avg(unsigned* data, unsigned count)
{
	int i;
	unsigned long val = 0;
	for (i=0;i<count;i++) val += data[i];
	return val/count;
}

static void
show_errors(bpm_det_state_t* bs) {
	fprintf(stderr, "Err: %d earlyMaxBooboo's\n", bs->earlyMaxBooboo);
}

// this function assumes finish>start
static void
diff_timespec(struct timespec* start, struct timespec* finish, struct timespec* result) {

	if (finish->tv_nsec<start->tv_nsec) {

		result->tv_sec = finish->tv_sec - start->tv_sec - 1;
		result->tv_nsec = finish->tv_nsec + 1000000000 - start->tv_nsec;
	} else {
		result->tv_sec  = finish->tv_sec - start->tv_sec;
		result->tv_nsec = finish->tv_nsec - start->tv_nsec;
	}

	return;
}
// return the time difference rounded to milliseconds
static unsigned
diff_timespec_ms(struct timespec* start, struct timespec* finish) {

 unsigned result_ms;
 struct timespec res;
 diff_timespec(start, finish, &res);

 result_ms = res.tv_sec*1000;
 result_ms += (res.tv_nsec+500000)/1000000;

 return result_ms;
}

void
Reset() {
	bs.b_i_idx = 0;
	bs.dtCount = bs.count = 0;
	bs.earlyMaxBooboo = 0;
	bs.consecutiveBeats = 0;

	memset(&bs, sizeof(bs), 0);
}


// interval at 30  bpm is 2000 ms
// interval at 200 bpm is 300 ms
int
legal_interval_range(unsigned beat_interval_ms)
{
 if (beat_interval_ms > 2000) return 0; // too high!
 if (beat_interval_ms < 300)  return 0; // too low!
 return 1; // GOOD!
}

//
// This routine updates the bs structure.
//
//
void
ProcessNextMeasurement(double val)
{
	struct timespec now;
	clock_gettime(sWhich_clock, &now);

	bs.justGenerated = 0; // by default, we only update state ...
	bs.count++;

	if (verbose>3) printf("%d: %f, s %ld, n %ld\n", bs.count, val, now.tv_sec, now.tv_nsec);

	if (bs.count > 1) {

		if (val < bs.prevVal) {
			bs.dtCount++;

			if (bs.dtCount == 1) {
				// tentative ...
				bs.prevMaxVal  = bs.prevVal;
				bs.prevMaxTime = bs.prevTime;
			}

			if (bs.dtCount == 5) {
				// ok, it's a true maxima!
				unsigned beat_interval_ms = diff_timespec_ms(
					&bs.prevBeatTime, &bs.prevMaxTime);	

				bs.prevBeatTime = bs.prevMaxTime;

//printf("computed interval %u\n", beat_interval_ms);
				// Is the previous heart beat from this person?
				if (legal_interval_range(beat_interval_ms)) {

					bs.consecutiveBeats++;
					bs.beat_intervals_ms[ bs.b_i_idx++ ] = beat_interval_ms;
					if (bs.b_i_idx >= AVERAGING_PULSES) bs.b_i_idx = 0;

					if (bs.consecutiveBeats >= AVERAGING_PULSES) {
						// legit bpm update and time (phase) goes with bs.prevBeatTime
 						bs.currentBeatInterval_ms = Avg(bs.beat_intervals_ms, AVERAGING_PULSES);
						bs.justGenerated = 1;
					}

				} else {
					bs.consecutiveBeats = 0;
				}
			}

		} else {

			if (bs.dtCount <= 5) {
				bs.earlyMaxBooboo++;
			}

			bs.dtCount = 0;
		}

	}

	bs.prevVal  = val;
	bs.prevTime = now;
}

void
Help() {
	fprintf(stderr, "PulsePolarBPM -v -iPODID\n"
		" -v for verbose output\n"
		" -iPODID  where PODID is a small number indicating this pod\n\n"
		" -aIPADDR  where IPADDR is an IPv4 dotted quad\n\n"
		" -pPORT where PORT is the port number\n\n");
}

void
Usage() { Help(); exit(1); }

void
GetOpts(int argc, char* argv[], uint8_t* pod_id, char** ip, short* port)
{
	int i;
	for (i = 1; i < argc; i++) {

		if (argv[i][0]=='-') {
			switch(argv[i][1]) {
			case 'h': Help();
			break;
			case 'a': *ip = argv[i]+2;
			break;
			case 'p': *port = atoi(argv[i]+2);
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

int main(int argc, char* argv[])
{
	char deviceName[GOIO_MAX_SIZE_DEVICE_NAME];
	gtype_int32 vendorId;		//USB vendor id
	gtype_int32 productId;		//USB product id
	char tmpstring[100];
	gtype_uint16 MajorVersion;
	gtype_uint16 MinorVersion;

	gtype_int32 rawMeasurement;
	gtype_real64 volts;
	gtype_real64 calbMeasurement;

	gtype_int32 numMeasurements,i;

	uint8_t pod_id = 1;
	char* ip = (char*)"192.168.1.255"; // default.
	short port = 1234;

	GetOpts(argc, argv, &pod_id, &ip, &port);

	printf("GoIO_DeviceCheck version 1.1\n");

	uint8_t sequence = 0; // packet sequence number
	int sock;
	struct sockaddr_in si_tobrain;

	if (SetupAnnounce_udp(ip, port, &sock, &si_tobrain) != 0) {
		printf("Can't init udp to '%s:%hd'\n", ip, port);
		return -1;
	}

	if (verbose>0) {
		printf("Use ip '%s' port %hd\n", ip, port);
	}

	Reset(); // reset the bpm state data.
	GoIO_Init();

	GoIO_GetDLLVersion(&MajorVersion, &MinorVersion);
	printf("This app is linked to GoIO lib version %d.%d .\n", MajorVersion, MinorVersion);

	bool bFoundDevice = GetAvailableDeviceName(deviceName, GOIO_MAX_SIZE_DEVICE_NAME, &vendorId, &productId);
	if (!bFoundDevice)
		printf("No Go devices found.\n");
	else
	{
		GOIO_SENSOR_HANDLE hDevice = GoIO_Sensor_Open(deviceName, vendorId, productId, 0);
		if (hDevice != NULL)
		{
			printf("Successfully opened %s device %s .\n", deviceDesc[productId], deviceName);

			unsigned char charId;
			GoIO_Sensor_DDSMem_GetSensorNumber(hDevice, &charId, 0, 0);
			printf("Sensor id = %d", charId);

			GoIO_Sensor_DDSMem_GetLongName(hDevice, tmpstring, sizeof(tmpstring));
			if (strlen(tmpstring) != 0)
				printf("(%s)", tmpstring);
			printf("\n");

			// period is in milliseconds. see above ...
			GoIO_Sensor_SetMeasurementPeriod(hDevice, MEASUREMENT_PERIOD, SKIP_TIMEOUT_MS_DEFAULT);
			GoIO_Sensor_SendCmdAndGetResponse(hDevice, SKIP_CMD_ID_START_MEASUREMENTS, NULL, 0, NULL, NULL, SKIP_TIMEOUT_MS_DEFAULT);

			//
			// MAIN LOOP - keep reading measurements forever ....
			// ... or until we read a command to stop on the network ...
			bool keepGoing = true;
			while (keepGoing) {
//printf("101\n");
				// block until one sample is ready ...
				numMeasurements = GoIO_Sensor_ReadRawMeasurements(hDevice, &rawMeasurement, 1);

				if (numMeasurements) {
					volts = GoIO_Sensor_ConvertToVoltage(hDevice, rawMeasurement);
					calbMeasurement = GoIO_Sensor_CalibrateData(hDevice, volts);

					ProcessNextMeasurement(calbMeasurement);

					if (bs.justGenerated) {

						AnnounceBPMdata_udp(
							bs.currentBeatInterval_ms, 
							diff_timespec_ms(&bs.prevBeatTime, &bs.prevTime),
							pod_id,
							sequence++,
							sock, &si_tobrain);

						if (verbose>0) {
							printf("period %f ms @%ld,%ld\n",
 								bs.currentBeatInterval_ms,
								bs.prevBeatTime.tv_sec,
								bs.prevBeatTime.tv_nsec);
						}
					}
				}

				// todo, calculate ms since last sample and subtract from 20
				OSSleep(10);
			}

			//GoIO_Sensor_DDSMem_GetCalibrationEquation(hDevice, &equationType);
			//gtype_real32 a, b, c;
			//unsigned char activeCalPage = 0;
			//GoIO_Sensor_DDSMem_GetActiveCalPage(hDevice, &activeCalPage);
			//GoIO_Sensor_DDSMem_GetCalPage(hDevice, activeCalPage, &a, &b, &c, units, sizeof(units));
			//printf("Average measurement = %8.3f %s .\n", averageCalbMeasurement, units);

			GoIO_Sensor_Close(hDevice);
		}
	}

	GoIO_Uninit();
	return 0;
}


bool GetAvailableDeviceName(char *deviceName, gtype_int32 nameLength, gtype_int32 *pVendorId, gtype_int32 *pProductId)
{
	bool bFoundDevice = false;
	deviceName[0] = 0;
	int numSkips = GoIO_UpdateListOfAvailableDevices(VERNIER_DEFAULT_VENDOR_ID, SKIP_DEFAULT_PRODUCT_ID);
	int numJonahs = GoIO_UpdateListOfAvailableDevices(VERNIER_DEFAULT_VENDOR_ID, USB_DIRECT_TEMP_DEFAULT_PRODUCT_ID);
	int numCyclopses = GoIO_UpdateListOfAvailableDevices(VERNIER_DEFAULT_VENDOR_ID, CYCLOPS_DEFAULT_PRODUCT_ID);
	int numMiniGCs = GoIO_UpdateListOfAvailableDevices(VERNIER_DEFAULT_VENDOR_ID, MINI_GC_DEFAULT_PRODUCT_ID);

	if (numSkips > 0)
	{
		GoIO_GetNthAvailableDeviceName(deviceName, nameLength, VERNIER_DEFAULT_VENDOR_ID, SKIP_DEFAULT_PRODUCT_ID, 0);
		*pVendorId = VERNIER_DEFAULT_VENDOR_ID;
		*pProductId = SKIP_DEFAULT_PRODUCT_ID;
		bFoundDevice = true;
	}
	else if (numJonahs > 0)
	{
		GoIO_GetNthAvailableDeviceName(deviceName, nameLength, VERNIER_DEFAULT_VENDOR_ID, USB_DIRECT_TEMP_DEFAULT_PRODUCT_ID, 0);
		*pVendorId = VERNIER_DEFAULT_VENDOR_ID;
		*pProductId = USB_DIRECT_TEMP_DEFAULT_PRODUCT_ID;
		bFoundDevice = true;
	}
	else if (numCyclopses > 0)
	{
		GoIO_GetNthAvailableDeviceName(deviceName, nameLength, VERNIER_DEFAULT_VENDOR_ID, CYCLOPS_DEFAULT_PRODUCT_ID, 0);
		*pVendorId = VERNIER_DEFAULT_VENDOR_ID;
		*pProductId = CYCLOPS_DEFAULT_PRODUCT_ID;
		bFoundDevice = true;
	}
	else if (numMiniGCs > 0)
	{
		GoIO_GetNthAvailableDeviceName(deviceName, nameLength, VERNIER_DEFAULT_VENDOR_ID, MINI_GC_DEFAULT_PRODUCT_ID, 0);
		*pVendorId = VERNIER_DEFAULT_VENDOR_ID;
		*pProductId = MINI_GC_DEFAULT_PRODUCT_ID;
		bFoundDevice = true;
	}

	return bFoundDevice;
}

void OSSleep(
	unsigned long msToSleep)//milliseconds
{
#ifdef TARGET_OS_WIN
	::Sleep(msToSleep);
#endif
#ifdef TARGET_OS_LINUX
  struct timeval tv;
  unsigned long usToSleep = msToSleep*1000;
  tv.tv_sec = usToSleep/1000000;
  tv.tv_usec = usToSleep % 1000000;
  select (0, NULL, NULL, NULL, &tv);
#endif
#ifdef TARGET_OS_MAC
	AbsoluteTime absTime = ::AddDurationToAbsolute(msToSleep * durationMillisecond, ::UpTime());
	::MPDelayUntil(&absTime);
#endif
}
