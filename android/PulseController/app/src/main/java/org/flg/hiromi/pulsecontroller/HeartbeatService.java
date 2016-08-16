package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class HeartbeatService extends Service {
    private boolean runOK = false;
    public interface HeartbeatListener {
        public void onBeat(Pulse pulse);
        public void onError(Throwable t);
    }

    private Set<HeartbeatListener> listeners = new LinkedHashSet<>();

    private Handler main = null;

    public class Channel extends Binder {
        private List<HeartbeatListener> channelListeners = new ArrayList<>();
        public void registerListener(HeartbeatListener listener) {
            channelListeners.add(listener);
            listeners.add(listener);
        }

        public void unregisterListeners() {
            listeners.removeAll(channelListeners);
        }
    }

    public void sendBeat(final Pulse pulse) {
        main.post(new Runnable() {
            @Override
            public void run() {
                for (HeartbeatListener hl: listeners) {
                    try {
                        hl.onBeat(pulse);
                    } catch (Exception | Error e) {
                        sendError(e);
                    }
                }
            }
        });
    }

    public void sendError(final Throwable e) {
        main.post(new Runnable() {
            @Override
            public void run() {
                for (HeartbeatListener hl: listeners) {
                    try {
                        hl.onError(e);
                    } catch (Exception | Error t) {
                        // Ignore
                    }
                }
            }
        });
    }

    private DatagramSocket openSocket(int port) {
        try {
            return new DatagramSocket(port);
        } catch (SocketException e) {
            sendError(e);
        }
        return null;
    }

    private DatagramSocket heartbeatSocket = null;
    public HeartbeatService() {
        super();
    }


    private final class HeartbeatThread extends Thread {
        public void run() {
            while (runOK) {
                byte[] data = new byte[20];
                DatagramPacket pkt = new DatagramPacket(data, data.length);
                try {
                    DatagramSocket s = heartbeatSocket;
                    if (s != null) {
                        s.receive(pkt);
                        if (pkt.getLength() >= 16) {
                            ByteBuffer buf = ByteBuffer.wrap(data);
                            Pulse pulse = new Pulse(
                                    buf.get(),
                                    buf.get(),
                                    buf.getShort(),
                                    buf.getInt(),
                                    buf.getFloat(),
                                    buf.getInt()
                            );
                            sendBeat(pulse);
                        }
                    }
                } catch (IOException e) {
                    sendError(e);
                }
            }
        }
    }

    private Thread heartbeatThread = null;

    @Override
    public void onCreate() {
        super.onCreate();
        main = new Handler(getMainLooper());
        heartbeatSocket = openSocket(5000);
        runOK = true;
        heartbeatThread = new HeartbeatThread();
        heartbeatThread.start();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return new Channel();
    }

    @Override
    public boolean onUnbind(Intent intent) {
        runOK = false;
        heartbeatThread = null;
        DatagramSocket s = heartbeatSocket;
        if (s != null) {
            heartbeatSocket = null;
            s.disconnect();
        }
        return super.onUnbind(intent);
    }
}
