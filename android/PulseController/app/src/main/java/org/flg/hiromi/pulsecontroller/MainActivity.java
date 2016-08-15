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
import android.widget.Button;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import android.content.Intent;

public class MainActivity extends ActionBarActivity {
    private TextView text_view;

    private PulseCommChannel commChannel;

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
            commChannel = (PulseCommChannel)service;
            commChannel.registerErrorWatcher(new PulseCommChannel.ErrWatcher() {
                @Override
                public void onError(Throwable t) {
                    Toast.makeText(MainActivity.this, "Error in REST service: " + t.toString(), Toast.LENGTH_LONG).show();
                }
            });
            initSeekbar(R.id.slider1);
            initButton(R.id.button);
            initButton(R.id.button2);
            initButton(R.id.button3);
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
     * @param id
     */
    public void initButton(int id)
    {
        final Button btnA = (Button)findViewById(id);
        commChannel.watchEvent((String) btnA.getTag(), new PulseCommChannel.IntWatcher() {
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
     * @param id
     */
    public void initSeekbar(int id){
        final SeekBar seek_bar = (SeekBar)findViewById(id);
        text_view = (TextView)findViewById(R.id.textView_status);
        text_view.setText(seek_bar.getTag() + " : " + seek_bar.getProgress() + " / " + seek_bar.getMax());
        commChannel.watchParameter((String)seek_bar.getTag(), new PulseCommChannel.IntWatcher() {
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
                    int progress_value;

                    @Override
                    public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                        progress_value = progress;
                        if (commChannel != null) {
                            commChannel.setIntParam((String)seekBar.getTag(), progress);
                        }
                    }

                    @Override
                    public void onStartTrackingTouch(SeekBar seekBar) {
                        //Toast.makeText(MainActivity.this, "SeekBar in StartTracking", Toast.LENGTH_LONG).show();
                    }

                    @Override
                    public void onStopTrackingTouch(SeekBar seekBar) {
                        //xtext_view.setText("Covered : " + progress_value + " / " + seek_bar.getMax());
                        //Toast.makeText(MainActivity.this, "SeekBar in StopTracking", Toast.LENGTH_LONG).show();
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
