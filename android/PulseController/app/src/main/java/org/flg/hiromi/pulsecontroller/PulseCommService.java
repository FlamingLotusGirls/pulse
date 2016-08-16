package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;

public class PulseCommService extends Service {

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
    public IBinder onBind(Intent intent) {
        channel = new RESTPulseCommChannel(this);
        handler.postDelayed(statusMon, 1000);
        return channel;
    }

    @Override
    public boolean onUnbind(Intent intent) {
        channel = null;
        return super.onUnbind(intent);
    }
}
