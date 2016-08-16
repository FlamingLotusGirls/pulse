package org.flg.hiromi.pulsecontroller;

import android.os.Binder;
import android.os.Handler;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Created by rwk on 2016-08-15.
 */
public abstract class BasePulseCommChannel extends Binder implements IPulseCommChannel {
    protected final List<StatusWatcher> statusWatchers = new ArrayList<>();
    protected final PulseCommService service;
    protected final Handler main;
    private final Map<String,List<IntWatcher>> watchers = new HashMap<>();
    private final List<ErrWatcher> errWatchers = new ArrayList<>();

    public BasePulseCommChannel(PulseCommService service) {
        this.service = service;
        main = new Handler(service.getMainLooper());
    }

    /**
     * Send an int value back to the main thread.
     */
    protected void sendBack(final String name, final int val, final boolean update) {
        main.post(new Runnable() {
            @Override
            public void run() {
                for (IntWatcher iw : getWatchers(name)) {
                    try {
                        iw.onChange(name, val, update);
                    } catch (Error | Exception t) {
                        Log.e("SVC", "Error while reporting change.", t);
                        sendError(t);
                    }
                }
            }
        });
    }

    // Send an error to any watchers/listeners.
    protected void sendError(final Throwable t) {
        main.post(new Runnable() {
            @Override
            public void run() {
                for (ErrWatcher ew : errWatchers) {
                    try {
                        Log.e("SVC", "Sending error to UI", t);
                        ew.onError(t);
                    } catch (Error | Exception t) {
                        Log.e("SVC", "Error while reporting error.", t);
                    }
                }
            }
        });
    }

    /**
     * Read a response from an HTTPConnection.
     * @param conn
     * @return
     * @throws IOException
     * @throws JSONException
     */
    protected JSONObject readResponse(HttpURLConnection conn) throws IOException, JSONException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        try {
            String jsonText = "";
            String line;
            while ((line = reader.readLine()) != null) {
                jsonText += line;
            }
            return new JSONObject(jsonText);
        } finally {
            reader.close();
        }
    }

    // Get a list of watchers by name. Never returns null.
    private List<IntWatcher> getWatchers(String name) {
        List<IntWatcher> ws = watchers.get(name);
        if (ws == null) {
            ws = new ArrayList<>();
            watchers.put(name, ws);
        }
        return ws;
    }

    /**
     * Watch for parameter changes
     * @param name Parameter name
     * @param cb Callback on parameter change
     */
    @Override
    public void watchParameter(String name, IntWatcher cb) {
        watchEvent(name, cb);
        getIntParam(name);
    }

    /**
     * Watch for events
     * @param name Parameter name
     * @param cb Callback on event
     */
    @Override
    public void watchEvent(String name, IntWatcher cb) {
        List<IntWatcher> ws = getWatchers(name);
        ws.add(cb);
    }

    /**
     * Register an {@link ErrWatcher} to be notified of any service errors.
     * @param watcher
     */
    @Override
    public void registerErrorWatcher(ErrWatcher watcher) {
        errWatchers.add(watcher);
    }

    /**
     * Register a {@link StatusWatcher} to be notified of connection and device status
     * @param watcher
     */
    @Override
    public void registerStatusWatcher(StatusWatcher watcher) {
        statusWatchers.add(watcher);
    }
}
