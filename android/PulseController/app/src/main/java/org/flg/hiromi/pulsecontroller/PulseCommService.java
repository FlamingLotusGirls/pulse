package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.widget.Toast;

public class PulseCommService extends Service {
    public PulseCommService() {
    }

    @Override
    public IBinder onBind(Intent intent) {
        Toast.makeText(getApplicationContext(), "Beep", Toast.LENGTH_LONG).show();
        return new PulseCommChannel(this);
    }
}
