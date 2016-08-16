package org.flg.hiromi.pulsecontroller;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketAddress;
import java.net.SocketException;
import java.net.UnknownHostException;

/**
 * Created by rwk on 2016-08-15.
 */

public class UDPPulseCommChannel extends BasePulseCommChannel {
    private final DatagramSocket cmdSocket;
    private final InetAddress broadcast;
    private InetAddress getBroadcast() {
        try {
            return InetAddress.getByName("10.0.2.2");
        } catch (UnknownHostException e) {
            sendError(e);
        }
        return null;
    }
    private DatagramSocket openSocket(int port) {
        try {
            return new DatagramSocket(port);
        } catch (SocketException e) {
            sendError(e);
        }
        return null;
    }
    public UDPPulseCommChannel(PulseCommService service) {
        super(service);
        broadcast = getBroadcast();
        cmdSocket = openSocket(5001);
    }

    // Does nothing on UDP.
    @Override
    public void getIntParam(String param) {
        sendBack(param, 1, false);
    }

    @Override
    public void setIntParam(String param, int value) {
        sendBack(param, value, false);
    }

    @Override
    public void trigger(String name) {
        sendBack(name, 1, false);
    }

    @Override
    public void readStatus() {
        try {
            final JSONObject status = new JSONObject();
            status.put("status", "UDP");
            main.post(new Runnable() {
                @Override
                public void run() {
                    for (StatusWatcher w : statusWatchers) {
                        try {
                            w.onStatus(status);
                        } catch (Exception | Error t) {
                            sendError(t);
                        }
                    }
                }
            });
        } catch (JSONException e) {
            sendError(e);
        }
    }
}
