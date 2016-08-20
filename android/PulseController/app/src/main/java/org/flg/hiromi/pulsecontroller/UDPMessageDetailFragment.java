package org.flg.hiromi.pulsecontroller;

import android.app.Activity;
import android.os.Bundle;
import android.support.design.widget.Snackbar;
import android.support.v4.app.Fragment;
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
     * The dummy content this fragment is presenting.
     */
    private UDPMessage mItem;

    private UDPMessageContext msgContext;

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
            msgContext = new UDPMessageContext(getActivity());

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
                            mItem.set(mItem.getOriginal());
                            setViews(rootView, mItem);
                            Snackbar.make(rootView, R.string.confirm_reverted, LENGTH_LONG).show();
                        }
                    }
                });
            }
        }
    }

    private void setViews(View rootView, UDPMessage msg) {
        View itemView = rootView.findViewById(R.id.udpmessage_detail);
        TextView typeView = (TextView)itemView.findViewById(R.id.view_type);
        typeView.setText(msg.getType());
        Spinner modules = (Spinner) itemView.findViewById(R.id.edit_receiver);
        final String[] receiverNames = msgContext.getReceiverNames();
        int receiverID = msg.getReceiverId();
        if (receiverID == UDPMessage.RECEIVER_BROADCAST) {
            receiverID = receiverNames.length - 1;
        }
        modules.setSelection(receiverID);
        Spinner cmd = (Spinner) itemView.findViewById(R.id.edit_command);
        cmd.setSelection(msg.getCommandId());
        EditText editData = (EditText) itemView.findViewById(R.id.edit_data);
        TextView viewData = (TextView) itemView.findViewById(R.id.view_data);
        editData.setText(Integer.toString(msg.getData()));
        if (!mItem.getNeedsData()) {
            editData.setEnabled(true);
            editData.setVisibility(View.VISIBLE);
            viewData.setVisibility(View.GONE);
        } else {
            editData.setEnabled(false);
            editData.setVisibility(View.GONE);
            viewData.setVisibility(View.VISIBLE);
        }
    }

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
                             Bundle savedInstanceState) {
        View rootView = inflater.inflate(R.layout.udpmessage_detail, container, false);

        if (mItem != null) {
            View itemView = rootView.findViewById(R.id.udpmessage_detail);
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
                    mItem.setReceiverId(position);
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
                    mItem.setCommandId(position);
                }

                @Override
                public void onNothingSelected(AdapterView<?> parent) {
                }
            });
            setViews(rootView, mItem);
        }

        return rootView;
    }
}
