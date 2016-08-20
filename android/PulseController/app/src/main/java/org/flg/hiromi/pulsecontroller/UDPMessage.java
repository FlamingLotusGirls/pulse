package org.flg.hiromi.pulsecontroller;

import android.content.Context;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.util.ArrayMap;

import java.net.DatagramPacket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Created by rwk on 2016-08-18.
 * Representation of and interface to UDP messages for our various events.
 * The trackingId is supplied at the time of converting it to a byte array.
 * This does not include Heartbeat events, which have a different structure.
 */
public class UDPMessage {
    public static final String TABLE_NAME = "messages";
    public static final String FIELD_ID = "_ID";
    public static final String FIELD_TYPE = "type";
    private static final String SELECT_TYPE = FIELD_TYPE + "=?";
    public static final String FIELD_TAG = "tag";
    public static final String FIELD_RECEIVER = "receiver";
    public static final String FIELD_COMMAND= "commmand";
    public static final String FIELD_DATA = "data";

    public static final String TYPE_TRIGGER = "trigger";
    public static final String TYPE_PARAM = "param";

    public static final int RECEIVER_BROADCAST = 255;

    private static final String[] COLUMNS = {
            FIELD_TAG, FIELD_RECEIVER, FIELD_COMMAND, FIELD_DATA
    };
    private final String tag;
    private final String type;
    private int receiverId;
    private int commandId;
    private boolean needsData;
    private int data;
    private final static AtomicInteger globalTracking = new AtomicInteger(0);

    // What was originally configured into the app
    private final UDPMessage original;
    /*
     * Build a UDPMMessage from an int[] array of either:
     * [receiverId, commandId]
     * or
     * [recieverId, commandId, data]
     * These come from the resources
     */
    public UDPMessage(String tag, int[] vals) {
        this.tag = tag;
        switch (vals.length) {
            case 3:
                data = vals[2];
                needsData = false;
                type = TYPE_TRIGGER;
                break;
            case 2:
                data = 0;
                needsData = true;
                type = TYPE_PARAM;
                break;
            default:
                throw new Error("Invalid UDPMessage " + tag + " data length: " + vals.length);
        }
        receiverId = vals[0];
        commandId = vals[1];
        original = null;
    }

    public UDPMessage(String tag, String type, int receiverId, int commandId, int data,
                      boolean needsData, UDPMessage original) {
        this.tag = tag;
        this.type = type;
        this.receiverId = receiverId;
        this.commandId = commandId;
        this.data = data;
        this.needsData = needsData;
        this.original = original;
    }

    public static Map<String,UDPMessage> loadOverrides(SQLiteDatabase db, String type,
                                                       Map<String,UDPMessage> originals) {
        Map<String,UDPMessage> map = new ArrayMap<>();
        Cursor c = db.query(TABLE_NAME, COLUMNS, SELECT_TYPE, new String[] {type}, null, null, null);
        while (c.moveToNext()) {
            String tag = c.getString(0);
            int receiver = c.getInt(1);
            int command = c.getInt(2);
            int data = c.isNull(3) ? 0 : c.getInt(3);
            UDPMessage original = originals.get(tag);
            UDPMessage msg = new UDPMessage(tag, type, receiver, command, data, c.isNull(3), original);
            map.put(tag, msg);
        }
        return map;
    }

    public static Map<String,UDPMessage> loadMessageMap(Context ctx, SQLiteDatabase db, String type, int namesId, int valsId) {
        Map<String,UDPMessage> map = new TreeMap<>();
        Resources rsrcs = ctx.getResources();
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
        map.putAll(loadOverrides(db, type, map));
        return map;
    }

    public static Map<String,UDPMessage> loadMessageMap(Context ctx) {
        try (SQLiteDatabase db = new UDPMessageDBHelper(ctx).getReadableDatabase()) {
            Map<String, UDPMessage> map = loadMessageMap(ctx, db, TYPE_TRIGGER,
                    R.array.trigger_names, R.array.triggers);
            map.putAll(loadMessageMap(ctx, db, TYPE_PARAM,
                    R.array.param_names, R.array.params));
            return map;
        }
    }

    public static UDPMessage getMessage(Context ctx, String name) {
        return loadMessageMap(ctx).get(name);
    }

    public String getTag() {
        return tag;
    }

    public String getType() {
        return type;
    }

    public int getReceiverId() {
        return receiverId;
    }

    public void setReceiverId(int receiverId) {
        this.receiverId = receiverId;
    }

    public int getCommandId() {
        return commandId;
    }

    public void setCommandId(int commandId) {
        this.commandId = commandId;
    }

    public int getData() {
        return data;
    }

    public void setData(int data) {
        this.data = data;
    }

    public boolean getNeedsData() {
        return needsData;
    }

    public byte[] toArray(ByteOrder order, int value) {
        ByteBuffer buffer = ByteBuffer.allocate(8);
        buffer.order(order);
        buffer.put((byte) receiverId);
        buffer.put((byte) globalTracking.getAndIncrement());
        buffer.putShort((short) commandId);
        buffer.putInt(needsData ? value : data);
        return buffer.array();
    }

    public String getContentString() {
        String msg = "rcv=" + receiverId + ", cmd=" + commandId;
        return msg + ", data=" + (needsData ? "*" : data);
    }

    public String getContentString(UDPMessageContext ctx) {
        String receiver = ctx.getReceiverName(receiverId);
        String cmd = ctx.getCommandName(commandId);
        String msg = "rcv=" + receiver + ", cmd=" + cmd;
        return msg + ", data=" + (needsData ? "*" : data);
    }

    public UDPMessage getOriginal() {
        return original;
    }

    public void set(UDPMessage o) {
        receiverId = o.getReceiverId();
        commandId = o.getCommandId();
        data = o.getData();
        needsData = o.getNeedsData();
    }

    @Override
    public UDPMessage clone() {
        // Allow reverting to the original configured value.
        UDPMessage nOriginal = (original == null) ? this : original;
        return new UDPMessage(tag, type, receiverId, commandId, data, needsData, nOriginal);
    }

    @Override
    public String toString() {
        return type + ":" + tag + "[" + getContentString() + "]";
    }
}
