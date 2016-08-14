package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.os.Binder;
import android.os.Handler;
import android.widget.Toast;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Created by rwk on 2016-08-13.
 */

public class PulseCommChannel extends Binder {
    public interface IntWatcher {
        public void onChange(String name, int val);
    }
    private final Map<String,List<IntWatcher>> watchers = new HashMap<>();
    private final PulseCommService service;
    private final Map<String,Integer> int_params = new HashMap<>();

    private final ExecutorService executor = Executors.newFixedThreadPool(2);
    private final Handler main;

    public PulseCommChannel(PulseCommService service) {
        this.service = service;
        main = new Handler(service.getMainLooper());
    }

    private void sendBack(final String name, final int val) {
        main.post(new Runnable() {
            @Override
            public void run() {
                for (IntWatcher iw : getWatchers(name)) {
                    iw.onChange(name, val);
                }
            }
        });
    }

    // Set a parameter to an integer value
    public void setIntParam(final String param, final int value) {
        executor.submit(new Runnable() {
            public void run() {
                try {
                    HttpURLConnection conn = (HttpURLConnection)new URL("http://10.0.2.2:8081/val?param=" + param + "&value=" + value).openConnection();
                    conn.setRequestMethod("PUT");
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    try {
                        String jsonText = "";
                        String line;
                        while ((line = reader.readLine()) != null) {
                            jsonText += line;
                        }
                        JSONObject obj = new JSONObject(jsonText);
                        sendBack(param, obj.getInt("value"));
                    } finally {
                        reader.close();
                    }
                } catch (IOException | JSONException e) {
                    throw new Error("Could not open connection: " + e);
                }
            }
        });
    }

    // Get an integer value.
    public void getIntParam(final String param) {
        executor.submit(new Runnable() {
            public void run() {
                try {
                    HttpURLConnection conn = (HttpURLConnection)new URL("http://10.0.2.2:8081/val?param=" + param ).openConnection();
                    conn.setRequestMethod("GET");
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    try {
                        String jsonText = "";
                        String line;
                        while ((line = reader.readLine()) != null) {
                            jsonText += line;
                        }
                        JSONObject obj = new JSONObject(jsonText);
                        sendBack(param, obj.getInt("value"));
                    } finally {
                        reader.close();
                    }
                } catch (IOException | JSONException e) {
                    throw new Error("Could not open connection: " + e);
                }
            }
        });
    }

    public void trigger(String name) {

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

    // Watch for changes
    public void watch(String name, IntWatcher cb) {
        List<IntWatcher> ws = getWatchers(name);
        ws.add(cb);
        getIntParam("param");
    }
}
