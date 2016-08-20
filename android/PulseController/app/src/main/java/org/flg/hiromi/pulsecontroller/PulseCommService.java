package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.IBinder;
import android.preference.PreferenceManager;

public class PulseCommService extends Service {
    private SharedPreferences prefs;

    private final Runnable statusMon = new Runnable() {
        @Override
        public void run() {
            if (channel != null) {
                channel.readStatus();
                handler.postDelayed(statusMon, 1000);
            }
        }
    };

    public PulseCommService() {
    }

    private IPulseCommChannel channel = null;
    private Handler handler = new Handler();

    @Override
    public void onCreate() {
        super.onCreate();
        prefs = PreferenceManager.getDefaultSharedPreferences(this);
    }

    @Override
    public IBinder onBind(Intent intent) {
        switch (prefs.getString("protocol", "UDP")) {
            case "REST":
                channel = new RESTPulseCommChannel(this);
                break;
            case "UDP":
                channel = new UDPPulseCommChannel(this);
                break;
            default:
                channel = null;
        }
        handler.postDelayed(statusMon, 1000);
        return channel;
    }

    @Override
    public boolean onUnbind(Intent intent) {
        channel = null;
        return super.onUnbind(intent);
    }
}
