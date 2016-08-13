package org.flg.hiromi.pulsecontroller;

import android.os.Bundle;
import android.support.v7.app.ActionBarActivity;
import android.view.Menu;
import android.view.MenuItem;
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

public class MainActivity extends ActionBarActivity {

    private static SeekBar seek_bar;
    private static TextView text_view;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        seekbar();
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
                        text_view.setText("Covered : " + progress + " / " + seek_bar.getMax());
                        Toast.makeText(MainActivity.this, "SeekBar in progress", Toast.LENGTH_LONG).show();
                    }

                    @Override
                    public void onStartTrackingTouch(SeekBar seekBar) {
                        Toast.makeText(MainActivity.this, "SeekBar in StartTracking", Toast.LENGTH_LONG).show();
                    }

                    @Override
                    public void onStopTrackingTouch(SeekBar seekBar) {
                        text_view.setText("Covered : " + progress_value + " / " + seek_bar.getMax());
                        Toast.makeText(MainActivity.this, "SeekBar in StopTracking", Toast.LENGTH_LONG).show();
                    }
                }
        );
    }

    public int getParam(String param) {
        try {
            HttpURLConnection conn = (HttpURLConnection)new URL("http://192.168.58.17:8081/val?param=" + param ).openConnection();
            conn.setRequestMethod("GET");
            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            try {
                String jsonText = "";
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonText += line;
                }
                JSONObject obj = new JSONObject(jsonText);
                return obj.getInt("value");
            } finally {
                reader.close();
            }
        } catch (IOException | JSONException e) {
            throw new Error("Could not open connection: " + e);
        }
    }

    public int setParam(String param, String value) {
        try {
            HttpURLConnection conn = (HttpURLConnection)new URL("http://192.168.58.17:8081/val?param=" + param + "&value=" + value).openConnection();
            conn.setRequestMethod("PUT");
            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            try {
                String jsonText = "";
                String line;
                while ((line = reader.readLine()) != null) {
                    jsonText += line;
                }
                JSONObject obj = new JSONObject(jsonText);
                return obj.getInt("value");
            } finally {
                reader.close();
            }
        } catch (IOException | JSONException e) {
            throw new Error("Could not open connection: " + e);
        }
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
