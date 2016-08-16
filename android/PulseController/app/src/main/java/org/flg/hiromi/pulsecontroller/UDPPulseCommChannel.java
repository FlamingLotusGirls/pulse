package org.flg.hiromi.pulsecontroller;

import java.net.DatagramSocket;
import java.net.SocketException;

/**
 * Created by rwk on 2016-08-15.
 */

public class UDPPulseCommChannel extends BasePulseCommChannel {
    private final DatagramSocket heartbeatSocket;
    private final DatagramSocket cmdSocket;
    private DatagramSocket openSocket(int port) {
        try {
            return new DatagramSocket(5000);
        } catch (SocketException e) {
            sendError(e);
        }
        return null;
    }
    public UDPPulseCommChannel(PulseCommService service) {
        super(service);
        heartbeatSocket = openSocket(5000);
        cmdSocket = openSocket(5001);
    }

    // Does nothing on UDP.
    @Override
    public void getIntParam(String param) {

    }

    @Override
    public void setIntParam(String param, int value) {

    }

    @Override
    public void trigger(String name) {

    }

    @Override
    public void readStatus() {

    }
}
