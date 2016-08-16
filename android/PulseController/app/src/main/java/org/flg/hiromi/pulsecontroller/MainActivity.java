package org.flg.hiromi.pulsecontroller;

import android.content.ComponentName;
import android.content.Context;
import android.content.ServiceConnection;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.os.IBinder;
import android.preference.PreferenceManager;
import android.support.v7.app.ActionBarActivity;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import android.content.Intent;

import org.json.JSONObject;

public class MainActivity extends ActionBarActivity {
    private TextView text_view;

    private IPulseCommChannel commChannel;

    private SharedPreferences prefs;

    //  connect to our background communication service.
    private ServiceConnection serviceConnection = new ServiceConnection() {
        /**
         * Once the service is connected, we hook up the uI
         * @param name
         * @param service
         */
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            commChannel = (IPulseCommChannel)service;
            commChannel.registerErrorWatcher(new IPulseCommChannel.ErrWatcher() {
                @Override
                public void onError(Throwable t) {
                    Toast.makeText(MainActivity.this, "Error in REST service: " + t.toString(), Toast.LENGTH_LONG).show();
                }
            });
            final int colorOK = getResources().getColor(R.color.colorOK);
            final int colorDisconnected = getResources().getColor(R.color.colorDisconnected);
            commChannel.registerStatusWatcher(new IPulseCommChannel.StatusWatcher() {
                @Override
                public void onStatus(JSONObject status) {
                    TextView text = (TextView)MainActivity.this.findViewById(R.id.textView_connect);
                    if (status != null) {
                        text.setText("Connected OK");
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

        private void initControls(View v) {
            if (v instanceof Button) {
                if (v.getTag() instanceof String) {
                    initButton((Button)v);
                }
            } else if (v instanceof SeekBar) {
                if (v.getTag() instanceof String) {
                    initSeekbar((SeekBar)v);
                }
            } else if (v instanceof ViewGroup) {
                ViewGroup p = (ViewGroup)v;
                for (int i = 0; i < p.getChildCount(); i++) {
                    initControls(p.getChildAt(i));
                }
            }
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            commChannel = null;
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = PreferenceManager
                .getDefaultSharedPreferences(this);
        setContentView(R.layout.activity_main);
    }

    @Override
    protected void onStart() {
        super.onStart();
        Intent intent = new Intent(this, PulseCommService.class);
        bindService(intent, serviceConnection, Context.BIND_AUTO_CREATE);
    }

    @Override
    protected void onStop() {
        unbindService(serviceConnection);
        super.onStop();
    }

    /**
     * Initialize a button. The button must have a tag field with the name of the event to send.
     * @param btnA
     */
    public void initButton(final Button btnA)
    {
        commChannel.watchEvent((String) btnA.getTag(), new IPulseCommChannel.IntWatcher() {
            @Override
            public void onChange(String name, int val, boolean update) {
                String state = (val == 0) ? "Failed" : "OK";
                text_view.setText(btnA.getTag() + " : " + state);
                // Set the button background back
                Drawable bg = (Drawable)btnA.getTag(R.id.button);
                if (bg != null) {
                    btnA.setBackground(bg);
                    btnA.setEnabled(true);
                }
            }
        });
        btnA.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View arg)
            {
                if (commChannel != null) {
                    text_view.setText(btnA.getTag() + " :");
                    commChannel.trigger((String) arg.getTag());
                    Drawable bg = btnA.getBackground();
                    btnA.setTag(R.id.button, bg);
                    // Set the button color to show it's currently being processed
                    btnA.setBackgroundColor(Color.BLUE);
                    btnA.setEnabled(false);
                }
            }

        });
    }

    /**
     * Initialize a seek bar. The seek bar must have a tag field with the name of the parameter to set.
     * @param seek_bar
     */
    public void initSeekbar(final SeekBar seek_bar) {
        text_view = (TextView)findViewById(R.id.textView_status);
        text_view.setText(seek_bar.getTag() + " : " + seek_bar.getProgress() + " / " + seek_bar.getMax());
        commChannel.watchParameter((String)seek_bar.getTag(), new IPulseCommChannel.IntWatcher() {
            @Override
            public void onChange(String name, int val, boolean update) {
                text_view.setText(seek_bar.getTag() + " : " + val + " / " + seek_bar.getMax());
                if (!update) {
                    seek_bar.setProgress(val);
                }
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
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        int id = item.getItemId();

        if (id == R.id.action_settings) {
            startActivity(new Intent().setClass(getApplicationContext(), SettingsActivity.class));
            return true;
        }

        return super.onOptionsItemSelected(item);
    }
}
