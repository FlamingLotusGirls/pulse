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

import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.*;
import android.net.Uri;
import android.content.Intent;

public class MainActivity extends ActionBarActivity {

    private static SeekBar seek_bar;
    private static TextView text_view;

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
            commChannel.watch("slider1", new PulseCommChannel.IntWatcher() {
                @Override
                public void onChange(String name, int val) {
                    text_view.setText("Covered : " + val + " / " + seek_bar.getMax());
                    seek_bar.setProgress(val);
                }
            });
            commChannel.registerErrorWatcher(new PulseCommChannel.ErrWatcher() {
                @Override
                public void onError(Throwable t) {
                    Toast.makeText(MainActivity.this, "Error in REST service: " + t.getMessage(), Toast.LENGTH_LONG).show();
                }
            });
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
        addButtonClickListner();
        seekbar();
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

    public void addButtonClickListner()
    {
        Button btnA = (Button)findViewById(R.id.button);
        btnA.setOnClickListener(new View.OnClickListener() {
            @Override

            public void onClick(View arg)
            {
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("http://www.satalaj.com"));
                startActivity(intent);
            }

        });
    }
    public void seekbar(){
        seek_bar = (SeekBar)findViewById(R.id.slider1);
        text_view = (TextView)findViewById(R.id.textView2);
        text_view.setText("Covered : " + seek_bar.getProgress() + " / " + seek_bar.getMax());

        seek_bar.setOnSeekBarChangeListener(
                new SeekBar.OnSeekBarChangeListener() {
                    int progress_value;

                    @Override
                    public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                        progress_value = progress;
                        if (commChannel != null) {
                            commChannel.setIntParam("slider1", progress);
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
