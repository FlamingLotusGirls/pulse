package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.preference.PreferenceManager;
import android.util.Log;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetSocketAddress;
import java.net.SocketException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import static org.flg.hiromi.pulsecontroller.Pulse.*;

public class HeartbeatService extends Service {
    private volatile boolean runOK = false;
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
        Log.e(PULSE, "Error", e);
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
        while (true) {
            try {
                DatagramSocket sock = new DatagramSocket(null);
                sock.setReuseAddress(true);
                sock.bind(new InetSocketAddress(5000));
                Log.i(PULSE, "Socket open on port 5000");
                return sock;
            } catch (SocketException e) {
                sendError(e);
            }
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                return null;
            }
        }
    }

    private DatagramSocket heartbeatSocket = null;
    public HeartbeatService() {
        super();
    }


    private final class HeartbeatThread extends Thread {
        public void run() {
            Log.i(PULSE, "PULSE Thread Started");
            while (runOK && heartbeatThread == this) {
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
                    } else {
                        Log.e(PULSE, "No Socket");
                    }
                } catch (IOException e) {
                    Log.e(PULSE, "Socket error", e);
                    sendError(e);
                }
            }
        }
    }

    private volatile Thread heartbeatThread = null;

    private void startThread() {
        Log.i(PULSE, "Starting PULSE Thread");
        if (!runOK) {
            int port = Integer.parseInt(PreferenceManager.getDefaultSharedPreferences(this)
                                            .getString("heartbeat_port", "5000"));
            heartbeatSocket = openSocket(port);
            runOK = true;
            if (heartbeatThread == null) {
                heartbeatThread = new HeartbeatThread();
                heartbeatThread.start();
            }
        }
    }

    @Override
    public void onCreate() {
        Log.i(PULSE, "Create Heartbeat");
        super.onCreate();
        main = new Handler(getMainLooper());
        startThread();
    }

    @Override
    public IBinder onBind(Intent intent) {
        Log.i(PULSE, "Bind Heartbeat");
        startThread();
        return new Channel();
    }

    @Override
    public boolean onUnbind(Intent intent) {
        Log.i(PULSE, "Unbind Heartbeat");
        return super.onUnbind(intent);
    }

    @Override
    public void onDestroy() {
        Log.i(PULSE, "Destroy Heartbeat Service");
        runOK = false;
        if (heartbeatThread != null) {
            heartbeatThread.interrupt();;
        }
        heartbeatThread = null;
        DatagramSocket s = heartbeatSocket;
        if (s != null) {
            heartbeatSocket = null;
            s.disconnect();
        }
        super.onDestroy();
    }
}
