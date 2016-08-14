package org.flg.hiromi.pulsecontroller;

import android.content.ComponentName;
import android.content.Context;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
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
                    Toast.makeText(MainActivity.this, "Error in REST service: " + t.getMessage(), Toast.LENGTH_LONG).show();
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

    public void initButton(int id)
    {
        Button btnA = (Button)findViewById(id);
        btnA.setOnClickListener(new View.OnClickListener() {
            @Override

            public void onClick(View arg)
            {
                if (commChannel != null) {
                    commChannel.trigger((String) arg.getTag());
                }
            }

        });
    }
    public void initSeekbar(int id){
        final SeekBar seek_bar = (SeekBar)findViewById(id);
        text_view = (TextView)findViewById(R.id.textView2);
        text_view.setText(seek_bar.getTag() + " : " + seek_bar.getProgress() + " / " + seek_bar.getMax());
        commChannel.watch((String)seek_bar.getTag(), new PulseCommChannel.IntWatcher() {
            @Override
            public void onChange(String name, int val) {
                text_view.setText("Covered : " + val + " / " + seek_bar.getMax());
                seek_bar.setProgress(val);
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

        //noinspection SimplifiableIfStatement
        if (id == R.id.action_settings) {
            return true;
        }

        return super.onOptionsItemSelected(item);
    }
}
