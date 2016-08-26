from effectlayer import EffectParameters
import datetime

class PulseEffectParameters(EffectParameters):
    targetFrameRate = 15.0
    lastHeartBeatStartTime = 0
    nextHeartBeatStartTime = 0
    bps = 0
    # regarding buttonState, there aren't actually any buttons in Pulse, so this is sorta boring.

    def secs_between_beats(self):
        return self.next_heartbeat_start_time() - self.last_heartbeat_start_time()

    def beat_amplitude(self):
        if self.bps == 0:
            return 0
        # print self.now(), self.last_heartbeat_start_time()
        norm = (self.now() - self.last_heartbeat_start_time())# / self.secs_between_beats()
        return 1.0 - norm# ** 2

    def time_dt(self):
        # EffectParameters time is an int, this returns a datetime object
        return datetime.datetime.fromtimestamp(self.time)

    def now(self):
        return (datetime.datetime.now() - datetime.datetime.fromtimestamp(0)).total_seconds()

    def last_heartbeat_start_time(self):
        ts = self.lastHeartBeatStartTime
        return ts if type(ts) is int else (ts - datetime.datetime.fromtimestamp(0)).total_seconds()

    def next_heartbeat_start_time(self):
        ts = self.nextHeartBeatStartTime
        return ts if type(ts) is int else (ts - datetime.datetime.fromtimestamp(0)).total_seconds()

    def __str__(self):
        return "Now: %s, lastHeartBeatTime %s, nextHeartBeatTime %s bps: %s" % (datetime.datetime.now(), self.lastHeartBeatStartTime, self.nextHeartBeatStartTime, self.bps)
