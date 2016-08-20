package org.flg.hiromi.pulsecontroller;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
import android.support.design.widget.Snackbar;
import android.support.v4.app.Fragment;
import android.support.v7.widget.RecyclerView;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Spinner;
import android.support.v7.widget.Toolbar;
import android.widget.TextView;


import static android.support.design.widget.Snackbar.*;

/**
 * A fragment representing a single UDPMessage detail screen.
 * This fragment is either contained in a {@link UDPMessageListActivity}
 * in two-pane mode (on tablets) or a {@link UDPMessageDetailActivity}
 * on handsets.
 */
public class UDPMessageDetailFragment extends Fragment {
    /**
     * The fragment argument representing the item ID that this fragment
     * represents.
     */
    public static final String ARG_ITEM_ID = "item_id";

    /**
     * The fragment argument with the adaptor to update.
     */

    public static final String ARG_ITEM_POSITION = "item_position";

    /**
     * The content this fragment is presenting.
     */
    private UDPMessage mItem;

    private int mPosition;
    /**
     * True if modified in this view.
     */
    private boolean m_dirty = false;

    private IUDPMessageContext msgContext;

    private final ServiceConnection msgContextServiceConn = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            msgContext = (IUDPMessageContext)service;
            View rootView = getView();
            populateList(rootView);
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            msgContext = null;
        }
    };

    /**
     * Mandatory empty constructor for the fragment manager to instantiate the
     * fragment (e.g. upon screen orientation changes).
     */
    public UDPMessageDetailFragment() {
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (getArguments().containsKey(ARG_ITEM_ID)) {
            // Load the message from the tag, and make a copy for editing.
            mItem = UDPMessage.getMessage(getActivity(), getArguments().getString(ARG_ITEM_ID)).clone();
            mPosition = getArguments().getInt(ARG_ITEM_POSITION);
        }
    }

    private void initUI() {
        final Activity activity = getActivity();
        Toolbar tb = (Toolbar) activity.findViewById(R.id.toolbar);
        if (tb != null) {
            String type = (mItem.getType() == "param") ? "Parameter Message " : "Trigger Message ";
            tb.setSubtitle(type + mItem.getTag());
        }
        Button revert = (Button) activity.findViewById(R.id.btn_revert);
        if (revert != null) {
            revert.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    final View rootView = activity.findViewById(R.id.udpmessage_detail);
                    if (mItem != null) {
                        msgContext.revert(mItem);
                        m_dirty = false;
                        updateCaller();
                        setViews(rootView);
                        Snackbar.make(rootView, R.string.confirm_reverted, LENGTH_LONG).show();
                    }
                }
            });
        }
        Button save = (Button)activity.findViewById(R.id.btn_save);
        if (save != null) {
            save.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    final View rootView = activity.findViewById(R.id.udpmessage_detail);
                    if (mItem != null) {
                        msgContext.save(mItem);
                        m_dirty = false;
                        updateCaller();
                        setViews(rootView);
                        Snackbar.make(rootView, R.string.confirm_saved, LENGTH_LONG).show();
                    }
                }
            });
        }
    }

    @Override
    public void onDestroy() {
        final Activity activity = getActivity();
        Button revert = (Button) activity.findViewById(R.id.btn_revert);
        if (revert != null) {
            revert.setOnClickListener(null);
        }
        Button save = (Button)activity.findViewById(R.id.btn_save);
        if (save != null) {
            save.setOnClickListener(null);
        }
        super.onDestroy();
    }

    private void updateDirty() {
        if (mItem != null) {
            if (m_dirty) {
                getActivity().setTitle(mItem.getTag() + " " + getString(R.string.unsaved));
            } else if (mItem.isOverride()) {
                getActivity().setTitle(mItem.getTag() + " " + getString(R.string.overriden));
            } else {
                getActivity().setTitle(mItem.getTag());
            }
        }
    }

    private void updateCaller() {
        RecyclerView rv = (RecyclerView)getActivity().findViewById(R.id.udpmessage_list);
        if (rv != null) {
            UDPMessageListActivity.SimpleItemRecyclerViewAdapter adapter =
                    (UDPMessageListActivity.SimpleItemRecyclerViewAdapter) rv.getAdapter();
            adapter.update(mPosition, mItem);
        }
    }

    private void setViews(View rootView) {
        View itemView = rootView.findViewById(R.id.udpmessage_detail);
        TextView typeView = (TextView)itemView.findViewById(R.id.view_type);
        typeView.setText(mItem.getType());
        Spinner modules = (Spinner) itemView.findViewById(R.id.edit_receiver);
        final String[] receiverNames = msgContext.getReceiverNames();
        int receiverID = mItem.getReceiverId();
        if (receiverID == UDPMessage.RECEIVER_BROADCAST) {
            receiverID = receiverNames.length - 1;
        }
        modules.setSelection(receiverID);
        Spinner cmd = (Spinner) itemView.findViewById(R.id.edit_command);
        cmd.setSelection(mItem.getCommandId());
        EditText editData = (EditText) itemView.findViewById(R.id.edit_data);
        TextView viewData = (TextView) itemView.findViewById(R.id.view_data);
        String dataNum = Integer.toString(mItem.getData());
        if (!editData.getText().toString().equals(dataNum)) {
            editData.setText(dataNum);
        }
        if (!this.mItem.getNeedsData()) {
            editData.setEnabled(true);
            editData.setVisibility(View.VISIBLE);
            viewData.setVisibility(View.GONE);
        } else {
            editData.setEnabled(false);
            editData.setVisibility(View.GONE);
            viewData.setVisibility(View.VISIBLE);
        }
        updateDirty();
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
                             Bundle savedInstanceState) {
        final View rootView = inflater.inflate(R.layout.udpmessage_detail, container, false);
        initUI();

        Intent svcIntent = new Intent(getContext(), UDPMessageDataService.class);
        getContext().bindService(svcIntent, msgContextServiceConn, Context.BIND_AUTO_CREATE);

        return rootView;
    }

    private void populateList(final View rootView) {
        if (mItem != null) {
            View itemView = rootView.findViewById(R.id.udpmessage_detail);
            final EditText data = (EditText)itemView.findViewById(R.id.edit_data);
            Spinner modules = (Spinner) itemView.findViewById(R.id.edit_receiver);
            final String[] receiverNames = msgContext.getReceiverNames();
            final ArrayAdapter<String> rcvAdapter = new ArrayAdapter<>(getActivity(),
                    android.R.layout.simple_spinner_dropdown_item,
                    receiverNames);
            modules.setAdapter(rcvAdapter);
            modules.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override
                public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    if (position == receiverNames.length - 1) {
                        position = UDPMessage.RECEIVER_BROADCAST;
                    }
                    if (mItem.getReceiverId() != position) {
                        mItem.setReceiverId(position);
                        m_dirty = true;
                        setViews(rootView);
                    }
                    data.clearFocus();
                }

                @Override
                public void onNothingSelected(AdapterView<?> parent) {
                }
            });
            Spinner cmd = (Spinner) itemView.findViewById(R.id.edit_command);
            final String[] cmdNames = getActivity().getResources().getStringArray(R.array.pulse_cmds);
            final ArrayAdapter<String> cmdAdaptor = new ArrayAdapter<String>(getActivity(),
                    android.R.layout.simple_spinner_dropdown_item,
                    cmdNames);
            cmd.setAdapter(cmdAdaptor);
            cmd.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override
                public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    if (mItem.getCommandId() != position) {
                        mItem.setCommandId(position);
                        m_dirty = true;
                        setViews(rootView);
                    }
                    data.clearFocus();
                }

                @Override
                public void onNothingSelected(AdapterView<?> parent) {
                }
            });
            data.addTextChangedListener(new TextWatcher() {
                @Override
                public void beforeTextChanged(CharSequence s, int start, int count, int after) {

                }

                @Override
                public void onTextChanged(CharSequence s, int start, int before, int count) {

                }

                @Override
                public void afterTextChanged(Editable s) {
                    if (s.length() > 0) {
                        try {
                            int data = Integer.parseInt(s.toString());
                            if (data != mItem.getData()) {
                                mItem.setData(data);
                                m_dirty = true;
                                setViews(rootView);
                            }
                        } catch (NumberFormatException e) {
                            Snackbar.make(rootView, e.toString(), LENGTH_LONG).show();
                        }
                    }
                }
            });
            setViews(rootView);
        }
    }

    @Override
    public void onStop() {
        if(m_dirty) {
            String msg = getString(R.string.changes_discarded, mItem.getTag());
            Snackbar.make(getView(), msg, LENGTH_LONG).show();
        }
        super.onStop();
    }
}
