package org.flg.hiromi.pulsecontroller;

import android.content.res.Resources;
import android.content.res.TypedArray;
import android.database.Cursor;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteQuery;
import android.preference.PreferenceManager;
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
import java.nio.ByteOrder;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Callable;

import static org.flg.hiromi.pulsecontroller.UDPMessageDBHelper.*;

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
                .getString("byteorder", "LE");
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
            param_map = loadMap(db, "param", R.array.param_names, R.array.params);
            trigger_map = loadMap(db, "trigger", R.array.trigger_names, R.array.triggers);
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
    private Map<String,UDPMessage> loadMap(SQLiteDatabase db, String type, int namesId, int valsId) {
        Map<String,UDPMessage> map = new ArrayMap<>();
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
                map.put(name, new UDPMessage(name, data));
            }
        }
        return loadOverrides(db, type, map);
    }
    private static final String SELECT_TYPE = FIELD_TYPE + "=?";
    private static final String[] COLUMNS = {
      FIELD_TAG, FIELD_RECEIVER, FIELD_COMMAND, FIELD_DATA
    };
    private Map<String,UDPMessage> loadOverrides(SQLiteDatabase db, String type, Map<String, UDPMessage> map) {
        Cursor c = db.query(TABLE_NAME, COLUMNS, SELECT_TYPE, new String[] {type}, null, null, null);
        while (c.moveToNext()) {
            String tag = c.getString(0);
            int receiver = c.getInt(1);
            int command = c.getInt(2);
            int data = c.isNull(3) ? 0 : c.getInt(3);
            UDPMessage msg = new UDPMessage(tag, receiver, command, data, c.isNull(3));
            map.put(tag, msg);
        }
        return map;
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
