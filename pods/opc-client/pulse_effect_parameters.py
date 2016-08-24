from effectlayer import EffectParameters

class PulseEffectParameters(EffectParameters):
    targetFrameRate = 15.0
    lastHeartBeatStartTime = 0
    nextHeartBeatStartTime = 0
    bps = 0
    # regarding buttonState, there aren't actually any buttons in Pulse, so this is sorta boring.

    def beat_progress(self):
        beat_duration = self.nextHeartBeatStartTime - self.lastHeartBeatStartTime
        if beat_duration == 0:
            return 0
        return (self.time - self.lastHeartBeatStartTime) / beat_duration

    def __str__(self):
        return "Time: %d, lastHeartBeatTime %s, nextHeartBeatTime %s bps: %s" % (self.time, self.lastHeartBeatStartTime, self.nextHeartBeatStartTime, self.bps)
