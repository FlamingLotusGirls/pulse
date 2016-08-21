package org.flg.hiromi.pulsecontroller;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
import android.support.annotation.NonNull;
import android.support.v7.app.AppCompatActivity;
import android.support.v7.widget.RecyclerView;
import android.support.v7.widget.Toolbar;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import android.support.v7.app.ActionBar;
import android.view.MenuItem;

import java.util.ArrayList;
import java.util.List;

import static org.flg.hiromi.pulsecontroller.UDPMessageDetailFragment.*;

/**
 * An activity representing a list of UDPMessage. This activity
 * has different presentations for handset and tablet-size devices. On
 * handsets, the activity presents a list of items, which when touched,
 * lead to a {@link UDPMessageDetailActivity} representing
 * item details. On tablets, the activity presents the list of items and
 * item details side-by-side using two vertical panes.
 */
public class UDPMessageListActivity extends AppCompatActivity {

    /**
     * Whether or not the activity is in two-pane mode, i.e. running on a tablet
     * device.
     */
    private boolean mTwoPane;

    private IUDPMessageContext msgContext;
    private ServiceConnection svcConn = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            msgContext = (IUDPMessageContext)service;
            setupRecyclerView();
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            msgContext = null;
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_udpmessage_list);

        Toolbar toolbar = (Toolbar) findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);
        toolbar.setTitle(getTitle());;

        // Show the Up button in the action bar.
        ActionBar actionBar = getSupportActionBar();
        if (actionBar != null) {
            actionBar.setDisplayHomeAsUpEnabled(true);
        }

        if (findViewById(R.id.udpmessage_detail_container) != null) {
            // The detail container view will be present only in the
            // large-screen layouts (res/values-w900dp).
            // If this view is present, then the
            // activity should be in two-pane mode.
            mTwoPane = true;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();

        Intent svcIntent = new Intent(this, UDPMessageDataService.class);
        bindService(svcIntent, svcConn, BIND_AUTO_CREATE);
    }

    @Override
    protected void onPause() {
        unbindService(svcConn);
        super.onPause();
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        int id = item.getItemId();
        if (id == android.R.id.home) {
            // This ID represents the Home or Up button. In the case of this
            // activity, the Up button is shown. Use NavUtils to allow users
            // to navigate up one level in the application structure. For
            // more details, see the Navigation pattern on Android Design:
            //
            // http://developer.android.com/design/patterns/navigation.html#up-vs-back
            //

            navigateUpTo(new Intent(this, MainActivity.class));
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    private void setupRecyclerView() {
        RecyclerView recyclerView = (RecyclerView)findViewById(R.id.udpmessage_list);
        List<UDPMessage> entries = new ArrayList<>();
        for (UDPMessage ent : msgContext.getMessageList()) {
            entries.add(ent.clone());
        }
        recyclerView.setAdapter(new SimpleItemRecyclerViewAdapter(entries));
    }

    public class SimpleItemRecyclerViewAdapter
            extends RecyclerView.Adapter<SimpleItemRecyclerViewAdapter.ViewHolder> {

        private final List<UDPMessage> mValues;
        private int selected_position = -1;

        public SimpleItemRecyclerViewAdapter dup() {
            List<UDPMessage> entries = new ArrayList<>();
            for (UDPMessage ent : mValues) {
                entries.add(ent.clone());
            };
            return new SimpleItemRecyclerViewAdapter(entries);
        }

        SimpleItemRecyclerViewAdapter(List<UDPMessage> items) {
            mValues = items;
        }

        public void update(int position, UDPMessage msg) {
            mValues.set(position, msg);
            notifyItemChanged(position);
        }

        @Override
        public ViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.udpmessage_list_content, parent, false);
            return new ViewHolder(view);
        }

        @Override
        public void onBindViewHolder(final ViewHolder holder, final int position) {
            holder.mItem = mValues.get(position);
            holder.mIdView.setText(mValues.get(position).getTag());
            String content = mValues.get(position).getContentString(msgContext);
            TextView ovr = (TextView)holder.mView.findViewById(R.id.overridden);
            if (ovr != null) {
                if (holder.mItem.isOverride()) {
                    ovr.setText(getString(R.string.overriden));
                } else {
                    ovr.setText("");
                }
            }
            TextView lbl = (TextView)holder.mView.findViewById(R.id.label_override);
            if (lbl != null) {
                if (holder.mItem.getLabel() != null) {
                    lbl.setText(holder.mItem.getLabel());
                } else {
                    lbl.setText("");
                }
            }
            holder.mContentView.setText(content);
            if (position == selected_position) {
                if (holder.mItem.isOverride()) {
                    holder.mView.setBackgroundResource(R.drawable.list_item_selected_override);
                } else {
                    holder.mView.setBackgroundResource(R.drawable.list_item_selected);
                }
            } else if (holder.mItem.isOverride()) {
                holder.mView.setBackgroundResource(R.drawable.list_item_override);
            } else {
                holder.mView.setBackgroundResource(R.drawable.list_item);
            }
            holder.mView.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    if (mTwoPane) {
                        int old_position = selected_position;
                        selected_position = position;
                        notifyItemChanged(position);
                        if (selected_position >= 0) {
                            notifyItemChanged(old_position);
                        }
                        Bundle arguments = new Bundle();
                        arguments.putString(ARG_ITEM_ID, holder.mItem.getTag());
                        arguments.putInt(ARG_ITEM_POSITION, position);
                        UDPMessageDetailFragment fragment = new UDPMessageDetailFragment();
                        fragment.setArguments(arguments);
                        getSupportFragmentManager().beginTransaction()
                                .replace(R.id.udpmessage_detail_container, fragment)
                                .commit();
                        findViewById(R.id.btn_revert).setVisibility(View.VISIBLE);
                        findViewById(R.id.btn_save).setVisibility(View.VISIBLE);
                    } else {
                        Context context = v.getContext();
                        Intent intent = new Intent(context, UDPMessageDetailActivity.class);
                        intent.putExtra(UDPMessageDetailFragment.ARG_ITEM_ID, holder.mItem.getTag());

                        context.startActivity(intent);
                    }
                }
            });
        }

        @Override
        public int getItemCount() {
            return mValues.size();
        }

        class ViewHolder extends RecyclerView.ViewHolder {
            final View mView;
            final TextView mIdView;
            final TextView mContentView;
            UDPMessage mItem;

            ViewHolder(View view) {
                super(view);
                mView = view;
                mIdView = (TextView) view.findViewById(R.id.id);
                mContentView = (TextView) view.findViewById(R.id.content);
            }

            @Override
            public String toString() {
                return super.toString() + " '" + mContentView.getText() + "'";
            }
        }
    }
}
