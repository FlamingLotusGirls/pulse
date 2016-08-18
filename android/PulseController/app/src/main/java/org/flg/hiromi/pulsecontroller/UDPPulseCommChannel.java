package org.flg.hiromi.pulsecontroller;

import android.content.res.Resources;
import android.content.res.TypedArray;
import android.util.ArrayMap;

import org.json.JSONException;
import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.nio.Buffer;
import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Callable;

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
            DatagramSocket sock = new DatagramSocket(null);
            sock.setReuseAddress(true);
            sock.setBroadcast(true);
            sock.bind(new
                    InetSocketAddress(5001));
            return sock;
        } catch (SocketException e) {
            sendError(e);
        }
        return null;
    }
    public UDPPulseCommChannel(PulseCommService service) {
        super(service, 3);
        broadcast = getBroadcast();
        cmdSocket = openSocket(5001);
    }

    // Does nothing on UDP.
    @Override
    public void getIntParam(String param) {
        sendBack(param, 1, false);
    }

    private Map<String,int[]> param_map = loadMap(R.array.param_names, R.array.params);
    private Map<String,int[]> trigger_map = loadMap(R.array.trigger_names, R.array.triggers);

    private Map<String,int[]> loadMap(int namesId, int valsId) {
        Map<String,int[]> map = new ArrayMap<>();
        Resources rsrcs = service.getResources();
        TypedArray values = rsrcs.obtainTypedArray(valsId);
        String[] names = rsrcs.getStringArray(namesId);
        if (values.length() != names.length) {
            throw new Error("Inconsistent resources");
        }
        for (int i = 0; i < names.length; i++) {
            String name = names[i];
            int valId = values.getResourceId(i, 0);
            if (valId != 0) {
                int[] data = rsrcs.getIntArray(valId);
                map.put(name, data);
            }
        }
        return map;
    }

    @Override
    public void setIntParam(final String param, final int value) {
        sendCmd(param_map, "param", param, value);
    }

    private void sendCmd(final Map<String,int[]> map, final String type, final String param, final int value) {
        run(param, new Callable<Void>() {
            @Override
            public Void call() throws Exception {
                ByteBuffer buffer = ByteBuffer.allocate(8);
                int[] ents = map.get(param);
                if (ents != null) {
                    try {
                        buffer.put((byte) ents[0]);
                        buffer.put((byte) ents[1]);
                        buffer.putShort((short) ents[2]);
                        buffer.putInt(ents[3]);
                        DatagramPacket pkt = new DatagramPacket(buffer.array(), 8);
                        pkt.setAddress(broadcast);
                        cmdSocket.send(pkt);
                        sendBack(param, value, false);
                    } catch (Exception | Error e) {
                        sendError(param, e);
                    }
                } else {
                    sendError(param, new Error("Unknown " + type + ": " + param));
                }
                return null;
            }
        });
    }

    @Override
    public void trigger(final String name) {
        sendCmd(trigger_map, "trigger", name, 1);
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
