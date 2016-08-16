package org.flg.hiromi.pulsecontroller;

import android.content.SharedPreferences;
import android.preference.PreferenceManager;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Created by rwk on 2016-08-13.
 */

public class RESTPulseCommChannel extends BasePulseCommChannel {

    private final SharedPreferences prefs;
    private final ExecutorService executor = Executors.newFixedThreadPool(3);
    private String BASE_URL;

    public RESTPulseCommChannel(PulseCommService service) {
        super(service);
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

    private int invoke(int methodID, int endpointID, Object...formatArgs) throws IOException, JSONException {
        String method = service.getString(methodID);
        String endpoint = service.getString(endpointID, formatArgs);
        return invoke(method, endpoint);
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

    @Override
    public void readStatus()  {
        run(new Callable<Void>() {
            @Override
            public Void call() {
                try {
                    String endpoint = service.getString(R.string.url_status);
                    String method = service.getString(R.string.url_status_method);
                    HttpURLConnection conn = (HttpURLConnection)new URL(BASE_URL + endpoint).openConnection();
                    conn.setRequestMethod(method);
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

    // Set a parameter to an integer value
    @Override
    public void setIntParam(final String param, final int value) {
        run(new Callable<Void>() {
            public Void call() throws Exception {
                sendBack(param, invoke(R.string.url_param_set_method, R.string.url_param_set, param, value), true);
                return null;
            }
        });
    }

    // Get an integer value.
    @Override
    public void getIntParam(final String param) {
        run(new Callable<Void>() {
            public Void call() throws Exception {
                sendBack(param, invoke(R.string.url_param_get_method, R.string.url_param_get, param), false);
                return null;
            }
        });
    }

    /**
     * Trigger an event named "name"
     * @param name
     */
    @Override
    public void trigger(final String name) {
        run(new Callable<Void>() {
            public Void call() throws Exception {
                sendBack(name, invoke(R.string.url_trigger_method, R.string.url_trigger, name), true);
                return null;
            }
        });
    }

    /**
     * Run an action on one of our background threads.
     * @param cb
     */
    protected void run(final Callable<?> cb) {
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
}
