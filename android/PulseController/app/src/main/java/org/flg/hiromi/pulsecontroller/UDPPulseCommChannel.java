package org.flg.hiromi.pulsecontroller;

import android.database.sqlite.SQLiteDatabase;
import android.preference.PreferenceManager;

import org.json.JSONException;
import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.nio.ByteOrder;
import java.util.Map;
import java.util.concurrent.Callable;

/**
 * Created by rwk on 2016-08-15.
 */

public class UDPPulseCommChannel extends BasePulseCommChannel {
    // The socket we will send commands on.
    private final DatagramSocket cmdSocket;

    // Get the address we broadcast to.
    // Default is suitable for emulator. Real devices on real networks will need to set by netmask.
    private InetAddress getBroadcast() {
        try {
            String ip = PreferenceManager.getDefaultSharedPreferences(service)
                    .getString("udp_broadcast_addr", "10.0.2.255");
            return InetAddress.getByName(ip);
        } catch (UnknownHostException e) {
            sendError(e);
        }
        return null;
    }

    private ByteOrder getByteOrder() {
        String bo = PreferenceManager.getDefaultSharedPreferences(service)
                .getString("byteorder", "BE");
        switch (bo) {
            case "LE": return ByteOrder.LITTLE_ENDIAN;
            case "BE": return  ByteOrder.BIG_ENDIAN;
            default: {
                sendError(new Error("Illegal byte order preference value: " + bo));
                return ByteOrder.LITTLE_ENDIAN;
            }
        }
    }

    // Open the socket we will use
    private DatagramSocket openSocket() {
        try {
            DatagramSocket sock = new DatagramSocket(null);
            sock.setReuseAddress(true);
            sock.setBroadcast(true);
            return sock;
        } catch (SocketException e) {
            sendError(e);
        }
        return null;
    }

    // Get the port number to use from the preferences
    private int getPort() {
        return Integer.parseInt(PreferenceManager.getDefaultSharedPreferences(service)
                .getString("cmd_port", "5001"));
    }

    // Construct a UDPPulseCommChannel
    public UDPPulseCommChannel(PulseCommService service) {
        super(service, 3);
        cmdSocket = openSocket();
        UDPMessageDBHelper dbHelper = new UDPMessageDBHelper(service);
        try (SQLiteDatabase db = dbHelper.getReadableDatabase()) {
            param_map = loadMessageMap(db, "param", R.array.param_names, R.array.params);
            trigger_map = loadMessageMap(db, "trigger", R.array.trigger_names, R.array.triggers);
        }
    }

    // Does nothing on UDP.
    // Might want to ask REST server, or watch UDP commands as they go by.
    @Override
    public void getIntParam(String param) {
        sendBack(param, 1, false);
    }

    private final Map<String,UDPMessage> param_map;
    private final Map<String,UDPMessage> trigger_map;

    // Load a map from trigger/parameter names to UDP packets
    // These are paired resource arrays, string-array and typed array of integer-array
    private Map<String,UDPMessage> loadMessageMap(SQLiteDatabase db, String type, int namesId, int valsId) {
        return UDPMessage.loadMessageMap(service, db, type, namesId, valsId);
    }

    // Send a command to set an int value. This
    @Override
    public void setIntParam(final String param, final int value) {
        sendCmd(param_map, "param", param, value);
    }

    /**
     * Send a command
     * @param map The command map to use (param or trigger)
     * @param type The type of command map (for error messages)
     * @param param The name of the param or trigger
     * @param value The value to set, if not provided in the packet structure.
     */
    private void sendCmd(final Map<String,UDPMessage> map, final String type, final String param, final int value) {
        run(param, new Callable<Void>() {
            @Override
            public Void call() throws Exception {
                UDPMessage msg = map.get(param);
                if (msg != null) {
                    try {
                        DatagramPacket pkt = new DatagramPacket(msg.toArray(getByteOrder(), value), 8);
                        pkt.setAddress(getBroadcast());
                        pkt.setPort(getPort());
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
