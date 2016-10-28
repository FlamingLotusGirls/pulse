package org.flg.hiromi.pulsecontroller;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.os.IBinder;
import android.preference.PreferenceManager;
import android.support.v4.app.NavUtils;
import android.support.v7.app.ActionBarActivity;
import android.util.Log;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.Button;
import android.widget.CompoundButton;
import android.widget.ImageView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.ToggleButton;

import org.json.JSONException;
import org.json.JSONObject;

import static org.flg.hiromi.pulsecontroller.Pulse.*;

/**
 * Created by rwk on 2016-08-20.
 */
public class BaseFLGActivity extends ActionBarActivity {
    private final int view_id;
    private TextView text_view;
    private IPulseCommChannel commChannel;
    private IUDPMessageContext msgContext;
    private SharedPreferences prefs;
    private ServiceConnection msgContextConn = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            Log.i(PULSE, "UDPMEssageService Connected");
            msgContext = (IUDPMessageContext)service;
            // Now that we have have our DB connected, fire up the UI, etc.
            Intent intent = new Intent(BaseFLGActivity.this, PulseCommService.class);
            bindService(intent, commServiceConnection, Context.BIND_AUTO_CREATE);
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            Log.i(PULSE, "UDPMEssageService Disconnected");
            msgContext = null;
        }
    };
    //  connect to our background communication service.
    private ServiceConnection commServiceConnection = new ServiceConnection() {
        private String getStatus(JSONObject status) {
            if (status == null) {
                // We get null status on connection failures.
                return null;
            }
            try {
                return status.getString("status");
            } catch (JSONException e) {
                return "OK";
            }
        }
        /**
         * Once the service is connected, we hook up the uI
         * @param name
         * @param service
         */
        @Override
        public void onServiceConnected(final ComponentName name, IBinder service) {
            Log.i(PULSE, "PulseCommService Connected");
            commChannel = (IPulseCommChannel)service;
            commChannel.registerErrorWatcher(new IPulseCommChannel.ErrWatcher() {
                @Override
                public void onError(Throwable t) {
                    onServiceError(name.flattenToShortString(), t);
                }
            });
            final int colorOK = getResources().getColor(R.color.colorOK);
            final int colorDisconnected = getResources().getColor(R.color.colorDisconnected);
            commChannel.registerStatusWatcher(new IPulseCommChannel.StatusWatcher() {
                @Override
                public void onStatus(JSONObject status) {
                    String stat = getStatus(status);
                    TextView text = (TextView)BaseFLGActivity. this.findViewById(R.id.textView_connect);
                    if (status != null) {
                        text.setText("Connected " + stat);
                        text.setTextColor(colorOK);
                    } else {
                        text.setText("Disconnected");
                        text.setTextColor(colorDisconnected);
                    }
                }
            });
            View v = findViewById(R.id.nandesuka);
            initControls(v);
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            Log.i(PULSE, "PulseCommService Disconnected");
            commChannel = null;
        }
    };
    private HeartbeatService.Channel beatChannel = null;
    private ServiceConnection pulseServiceConnection = new ServiceConnection() {
        // Map the podID to the right icon.
        private ImageView chooseIcon(int podId) {
            ImageView pulse_icon_1 = (ImageView)findViewById(R.id.pulse_icon_1);
            ImageView pulse_icon_2 = (ImageView)findViewById(R.id.pulse_icon_2);
            ImageView pulse_icon_3 = (ImageView)findViewById(R.id.pulse_icon_3);
            ImageView pulse_icon_4 = (ImageView)findViewById(R.id.pulse_icon_4);
            ImageView pulse_icon_5 = (ImageView)findViewById(R.id.pulse_icon_5);
            switch (podId % 5) {
                case 0: return pulse_icon_5;
                case 1: return pulse_icon_4;
                case 2: return pulse_icon_3;
                case 3: return pulse_icon_2;
                case 4: return pulse_icon_1;
            }
            return null;
        }
        @Override
        public void onServiceConnected(final ComponentName name, IBinder service) {
            Log.i(PULSE, "HeartbeatService Connected");
            beatChannel = (HeartbeatService.Channel)service;
            final float iy = chooseIcon(0).getY();
            beatChannel.registerListener(new HeartbeatService.HeartbeatListener() {
                @Override
                public void onBeat(Pulse pulse) {
                    // Only do anything if this is a valid pulse - bpm needs to be non-zero, etc
                    if (pulse.getInterval() > 0 && pulse.getBpm() > 0) {
                        final ImageView icon = chooseIcon(pulse.getPod());
                        if (icon != null) {
                            try {
                                icon.animate()
                                        .setDuration(50)
                                        .y(iy + 7)
                                        .scaleX(.5f)
                                        .scaleY(.5f)
                                        .withEndAction(new Runnable() {
                                            @Override
                                            public void run() {
                                                icon.animate()
                                                        .setDuration(270)
                                                        .y(iy)
                                                        .scaleX(1)
                                                        .scaleY(1);
                                            }
                                        });
                            } catch (Error | Exception e) {
                                onError(e);
                            }
                        }
                    }
                }
                @Override
                public void onError(Throwable t) {
                    onServiceError(name.flattenToShortString(), t);
                }
            });
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            Log.i(PULSE, "HeartbeatService Disconnected");
            beatChannel.unregisterListeners();
        }
    };

    protected BaseFLGActivity(int view_id) {
        this.view_id = view_id;
    }

    private void onServiceError(String name, Throwable t) {
        Log.e(PULSE, "Service Error: " + name, t);
        String msg = t.getMessage();
        msg = t.getClass().getSimpleName() + (msg == null ? "" : ": " + msg);
        text_view.setText("Error: " + msg);
    }

    private void initControls(View v) {
        if (v instanceof CompoundButton) {
            if (v.getTag() instanceof String) {
                initToggle((CompoundButton)v);
            }
        } else if (v instanceof SeekBar) {
            if (v.getTag() instanceof String) {
                initSeekbar((SeekBar) v);
            }
        } else if (v instanceof Spinner) {
            if (v.getTag() instanceof String) {
                initSpinner((Spinner)v);
            }
        } else if (v instanceof ViewGroup) {
            ViewGroup p = (ViewGroup)v;
            for (int i = 0; i < p.getChildCount(); i++) {
                initControls(p.getChildAt(i));
            }
        } else if (v instanceof Button) {
            if (v.getTag() instanceof String) {
                initButton((Button) v);
            }
        } else if (v instanceof TextView) {
            if (v.getTag() instanceof String) {
                initLabel((TextView)v);
            }
        }
    }

    @Override
    protected void onResume() {
        Log.i(PULSE, "Resume Activity");
        super.onResume();
        startServices();
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        Log.i(PULSE, "Create Activity");
        super.onCreate(savedInstanceState);
        prefs = PreferenceManager
                .getDefaultSharedPreferences(this);
        setContentView(view_id);
        text_view = (TextView)findViewById(R.id.textView_status);
    }

    @Override
    protected void onPause() {
        Log.i(PULSE, "Pause Activity");
        stopServices();
        super.onPause();
    }

    @Override
    protected void onStart() {
        Log.i(PULSE, "Start Activity");
        super.onStart();
    }

    private void startServices() {
        Log.i(PULSE, "Start Services");
        Intent intent = new Intent(this, UDPMessageDataService.class);
        bindService(intent, msgContextConn, Context.BIND_AUTO_CREATE);
        Intent intent2 = new Intent(this, HeartbeatService.class);
        bindService(intent2, pulseServiceConnection, Context.BIND_AUTO_CREATE);
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        Log.i(PULSE, "Configuration Changed");
        super.onConfigurationChanged(newConfig);
        setContentView(R.layout.activity_main);
        text_view = (TextView)findViewById(R.id.textView_status);
        View v = findViewById(R.id.nandesuka);
        initControls(v);
    }

    @Override
    protected void onStop() {
        Log.i(PULSE, "Stop Activity");
        super.onStop();
    }

    private void stopServices() {
        Log.i(PULSE, "Stop Services");
        unbindService(commServiceConnection);
        unbindService(pulseServiceConnection);
        unbindService(msgContextConn);
    }

    private void resetButton(Button btnA) {
        // Set the button background back
        Drawable bg = (Drawable) btnA.getTag(R.id.button_background);
        if (bg != null) {
            btnA.setBackground(bg);
            btnA.setEnabled(true);
        }
    }

    /**
     * Initialize a button. The button must have a tag field with the name of the event to send.
     * @param btnA
     */
    public void initButton(final Button btnA)
    {
        final Object tagv = (String)btnA.getTag();
        final String tag = (tagv instanceof String) ? (String)tagv : null;
        commChannel.watchEvent((String) tag, new IPulseCommChannel.IntWatcher() {
            @Override
            public void onChange(String name, int val, boolean update) {
                String state = (val == 0) ? "Failed" : "OK";
                text_view.setText(tag + ": " + state);
                resetButton(btnA);
            }

            @Override
            public void onError(String name, Throwable t) {
                onServiceError(name, t);
                // Set the button background back
                Drawable bg = (Drawable)btnA.getTag(R.id.button_background);
                resetButton(btnA);
            }
        });
        btnA.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View arg)
            {
                if (commChannel != null) {
                    text_view.setText(tag + ": ");
                    commChannel.trigger(tag);
                    Drawable bg = btnA.getBackground();
                    btnA.setTag(R.id.button_background, bg);
                    // Set the button color to show it's currently being processed
                    btnA.setBackgroundColor(Color.BLUE);
                    btnA.setEnabled(false);
                }
            }

        });
        String label = msgContext.getLabel(tag);
        if (label != null) {
            btnA.setText(label);
        }
    }

    public void initToggle(final CompoundButton btnA)
    {
        final Object tagv = (String)btnA.getTag();
        final String tag = (tagv instanceof String) ? (String)tagv : null;
        if (tag != null) {
            final String tag_on = tag + "_on";
            final String tag_off = tag + "_off";
            IPulseCommChannel.IntWatcher watcher = new IPulseCommChannel.IntWatcher() {
                @Override
                public void onChange(String name, int val, boolean update) {
                    String state = (val == 0) ? "Failed" : "OK";
                    text_view.setText(name + ": " + state);
                }

                @Override
                public void onError(String name, Throwable t) {
                    onServiceError(name, t);
                }
            };
            commChannel.watchEvent(tag_on, watcher);
            commChannel.watchEvent(tag_off, watcher);
            btnA.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
                @Override
                public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                    if (commChannel != null) {
                        String stateTag = isChecked ? tag_on : tag_off;
                        text_view.setText(stateTag + ": ");
                        commChannel.trigger(stateTag);
                        if (btnA instanceof Switch) {
                            String label = msgContext.getLabel(stateTag);
                            if (label != null) {
                                btnA.setText(label);
                            }
                        }
                    }
                }
            });
            if (btnA instanceof Switch) {
                String label = msgContext.getLabel(tag_off);
                if (label != null) {
                    btnA.setText(label);
                }
            }
        }
    }

    public void initSpinner(final Spinner spinner) {
        commChannel.watchEvent((String) spinner.getTag(), new IPulseCommChannel.IntWatcher() {
            @Override
            public void onChange(String name, int val, boolean update) {
                Object item = spinner.getItemAtPosition(val);
                text_view.setText(name + ": " + item);
            }

            @Override
            public void onError(String name, Throwable t) {
                onServiceError(name, t);
            }
        });
        spinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (position > 0) {
                    String tag = (String) spinner.getTag();
                    text_view.setText(tag + ": ");
                    if (commChannel != null) {
                        commChannel.setIntParam(tag, position - 1);
                    }
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {

            }
        });
    }

    private void initLabel(TextView v) {
        String tag = (String)v.getTag();
        String label = msgContext.getLabel(tag);
        if (label != null) {
            v.setText(label);
        }
    }

    /**
     * Initialize a seek bar. The seek bar must have a tag field with the name of the parameter to set.
     * @param seek_bar
     */
    public void initSeekbar(final SeekBar seek_bar) {
        text_view.setText(seek_bar.getTag() + ": " + seek_bar.getProgress() + " / " + seek_bar.getMax());
        commChannel.watchParameter((String)seek_bar.getTag(), new IPulseCommChannel.IntWatcher() {
            @Override
            public void onChange(String name, int val, boolean update) {
                text_view.setText(seek_bar.getTag() + " : " + val + " / " + seek_bar.getMax());
                if (!update) {
                    seek_bar.setProgress(val);
                }
            }

            @Override
            public void onError(String name, Throwable t) {
                onServiceError(name, t);
            }
        });
        seek_bar.setOnSeekBarChangeListener(
                new SeekBar.OnSeekBarChangeListener() {

                    @Override
                    public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                    }

                    @Override
                    public void onStartTrackingTouch(SeekBar seekBar) {
                    }

                    @Override
                    public void onStopTrackingTouch(SeekBar seekBar) {
                        int progress= seekBar.getProgress();
                        if (commChannel != null) {
                            commChannel.setIntParam((String)seekBar.getTag(), progress);
                        }
                    }
                }
        );
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        int id = item.getItemId();
        switch (id) {
            case android.R.id.home:
                NavUtils.navigateUpFromSameTask(this);
                return true;
            case R.id.action_settings:
                startActivity(new Intent().setClass(getApplicationContext(), SettingsActivity.class));
                return true;
            case R.id.udp_messages:
                startActivity(new Intent().setClass(getApplicationContext(), UDPMessageListActivity.class));
                return true;
            case R.id.main:
                startActivity(new Intent().setClass(getApplicationContext(), MainActivity.class));
                return true;
            case R.id.more:
                startActivity(new Intent().setClass(getApplicationContext(), MoreButtonsActivity.class));
                return true;
        }

        return super.onOptionsItemSelected(item);
    }
}
