package org.flg.hiromi.pulsecontroller;

import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.view.Menu;

public class MoreButtonsActivity extends BaseFLGActivity {

   public MoreButtonsActivity() {
       super(R.layout.activity_more);
   }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        // Inflate the menu; this adds items to the action bar if it is present.
        getMenuInflater().inflate(R.menu.menu_more, menu);
        return true;
    }
}
