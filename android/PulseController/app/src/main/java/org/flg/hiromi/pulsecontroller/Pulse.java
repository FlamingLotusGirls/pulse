package org.flg.hiromi.pulsecontroller;

/**
 * Created by rwk on 2016-08-16.
 */

public class Pulse {
    public static final String PULSE = "PULSE";
    private final int pod;
    private final int seq;
    private final int interval;
    private final int elapsed;
    private final float bpm;
    private final int time;
    public Pulse(int pod, int seq, int interval, int elapsed, float bpm, int time) {
        this.pod = pod;
        this.seq = seq;
        this.interval = interval;
        this.elapsed = elapsed;
        this.bpm = bpm;
        this.time = time;
    }
    public int getPod() {
        return pod;
    }

    public int getSeq() {
        return seq;
    }

    public int getInterval() {
        return interval;
    }

    public int getElapsed() {
        return elapsed;
    }

    public float getBpm() {
        return bpm;
    }

    public int getTime() {
        return time;
    }
}

