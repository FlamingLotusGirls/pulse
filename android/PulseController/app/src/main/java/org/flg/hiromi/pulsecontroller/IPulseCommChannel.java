package org.flg.hiromi.pulsecontroller;

import android.os.IBinder;

import org.json.JSONObject;

/**
 * Created by rwk on 2016-08-15.
 */
public interface IPulseCommChannel extends IBinder {
    void readStatus();

    // Set a parameter to an integer value
    void setIntParam(String param, int value);

    // Get an integer value.
    void getIntParam(String param);

    void trigger(String name);

    void watchParameter(String name, IntWatcher cb);

    void watchEvent(String name, IntWatcher cb);

    void registerErrorWatcher(ErrWatcher watcher);

    void registerStatusWatcher(StatusWatcher watcher);

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

        public void onError(String name, Throwable t);
    }

    public interface StatusWatcher {
        public void onStatus(JSONObject status);
    }
}
