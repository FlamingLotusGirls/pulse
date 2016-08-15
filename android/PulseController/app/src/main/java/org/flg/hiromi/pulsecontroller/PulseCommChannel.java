package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Binder;
import android.os.Handler;
import android.preference.PreferenceManager;
import android.util.Log;
import android.widget.Toast;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Callable;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Created by rwk on 2016-08-13.
 */

public class PulseCommChannel extends Binder {
    public interface ErrWatcher {
        public void onError(Throwable t);
    }

    public interface IntWatcher {
        /**
         *
         * @param name Name of the parameter changed
         * @param val New value of the parameter
         * @param update true if this is the result of an update.
         */
        public void onChange(String name, int val, boolean update);
    }

    public interface StatusWatcher {
        public void onStatus(JSONObject status);
    }
    private final Map<String,List<IntWatcher>> watchers = new HashMap<>();
    private final List<ErrWatcher> errWatchers = new ArrayList<>();
    private final List<StatusWatcher> statusWatchers = new ArrayList<>();
    private final PulseCommService service;

    private final ExecutorService executor = Executors.newFixedThreadPool(3);

    private final Handler main;
    private final SharedPreferences prefs;
    private String BASE_URL;

    public PulseCommChannel(PulseCommService service) {
        this.service = service;
        main = new Handler(service.getMainLooper());
        prefs = PreferenceManager
                .getDefaultSharedPreferences(service);
        BASE_URL = prefs.getString("base_url", "http://10.0.2.2:8081");
        prefs.registerOnSharedPreferenceChangeListener(new SharedPreferences.OnSharedPreferenceChangeListener() {
            @Override
            public void onSharedPreferenceChanged(SharedPreferences sharedPreferences, String key) {
                BASE_URL = prefs.getString("base_url", "http://10.0.2.2:8081");
            }
        });
    }

    /**
     * Run an action on one of our background threads.
     * @param cb
     */
    private void run(final Callable<?> cb) {
        executor.submit(new Runnable() {
            @Override
            public void run() {
                try {
                    cb.call();
                } catch (Exception | Error t) {
                    sendError(t);
                }
            }
        });
    }

    /**
     * Send an int value back to the main thread.
     */
    private void sendBack(final String name, final int val, final boolean update) {
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
    private void sendError(final Throwable t) {
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
    private JSONObject readResponse(HttpURLConnection conn) throws IOException, JSONException {
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

    private int invoke(String method, String endpoint) throws IOException, JSONException {
        HttpURLConnection conn = (HttpURLConnection)new URL(BASE_URL + endpoint).openConnection();
        conn.setRequestMethod(method);
        JSONObject obj = readResponse(conn);
        if (obj.getString("status").equals("OK")) {
            if (obj.has("value")) {
                return obj.getInt("value");
            }
            return 1;
        }
        throw new RuntimeException(("Error:" + obj.getString("message")));
    }

    public void readStatus()  {
        run(new Callable<Void>() {
            @Override
            public Void call() {
                try {
                    HttpURLConnection conn = (HttpURLConnection)new URL(BASE_URL + "/status").openConnection();
                    final JSONObject status = readResponse(conn);
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
                } catch (IOException | JSONException e) {
                    main.post(new Runnable() {
                        @Override
                        public void run() {
                            for (StatusWatcher w : statusWatchers) {
                                try {
                                    w.onStatus(null);
                                } catch (Exception | Error t) {
                                    sendError(t);
                                }
                            }
                        }
                    });
                }
                return null;
            }
        });
    }

    private static final String PUT = "PUT";
    private static final String GET = "GET";

    // Set a parameter to an integer value
    public void setIntParam(final String param, final int value) {
        run(new Callable<Void>() {
            public Void call() throws Exception {
                sendBack(param, invoke(PUT, "/val?param=" + param + "&value=" + value), true);
                return null;
            }
        });
    }

    // Get an integer value.
    public void getIntParam(final String param) {
        run(new Callable<Void>() {
            public Void call() throws Exception {
                sendBack(param, invoke(GET, "/val?param=" + param), false);
                return null;
            }
        });
    }

    /**
     * Trigger an event named "name"
     * @param name
     */
    public void trigger(final String name) {
        run(new Callable<Void>() {
            public Void call() throws Exception {
                sendBack(name, invoke(PUT, "/trigger?name=" + name), true);
                return null;
            }
        });
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
    public void watchParameter(String name, IntWatcher cb) {
        watchEvent(name, cb);
        getIntParam(name);
    }

    /**
     * Watch for events
     * @param name Parameter name
     * @param cb Callback on event
     */
    public void watchEvent(String name, IntWatcher cb) {
        List<IntWatcher> ws = getWatchers(name);
        ws.add(cb);
    }

    /**
     * Register an {@link ErrWatcher} to be notified of any service errors.
     * @param watcher
     */
    public void registerErrorWatcher(ErrWatcher watcher) {
        errWatchers.add(watcher);
    }

    /**
     * Register a {@link StatusWatcher} to be notified of connection and device status
     * @param watcher
     */
    public void registerStatusWatcher(StatusWatcher watcher) {
        statusWatchers.add(watcher);
    }
}
