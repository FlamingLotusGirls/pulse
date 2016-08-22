package org.flg.hiromi.pulsecontroller;

import android.content.Intent;
import android.support.v4.app.NavUtils;
import android.support.v7.app.AppCompatActivity;
import android.view.MenuItem;

/**
 * Created by rwk on 2016-08-22.
 */
public class BasePulseActivity extends AppCompatActivity {
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
