package org.flg.hiromi.pulsecontroller;

import java.net.DatagramPacket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Created by rwk on 2016-08-18.
 * Representation of and interface to UDP messages for our various events.
 * The trackingId is supplied at the time of converting it to a byte array.
 * This does not include Heartbeat events, which have a different structure.
 */
public class UDPMessage {
    private String tag;
    private int receiverId;
    private int commandId;
    private boolean needsData;
    private int data;
    private final static AtomicInteger globalTracking = new AtomicInteger(0);
    /*
     * Build a UDPMMessage from an int[] array of either:
     * [receiverId, commandId]
     * or
     * [recieverId, commandId, data]
     * These come from the resources
     */
    public UDPMessage(String tag, int[] vals) {
        switch (vals.length) {
            case 3:
                data = vals[2];
                needsData = false;
                break;
            case 2:
                data = 0;
                needsData = true;
                break;
            default:
                throw new Error("Invalid UDPMessage " + tag + " data length: " + vals.length);
        }
        receiverId = vals[0];
        commandId = vals[1];
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

    public byte[] toArray(ByteOrder order) {
        if (needsData) {
            throw new RuntimeException("Needs data: " + tag);
        }
        ByteBuffer buffer = ByteBuffer.allocate(8);
        buffer.order(order);
        buffer.put((byte) receiverId);
        buffer.put((byte) globalTracking.getAndIncrement());
        buffer.putShort((short) commandId);
        buffer.putInt(data);
        return buffer.array();
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
}
