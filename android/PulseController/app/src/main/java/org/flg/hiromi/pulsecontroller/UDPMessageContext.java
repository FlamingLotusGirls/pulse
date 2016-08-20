package org.flg.hiromi.pulsecontroller;

import android.content.Context;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Wraps a {@link Context} object and caches the UDPMessage data
 */

public class UDPMessageContext {
    private final Context context;
    public UDPMessageContext(Context ctx) {
        context = ctx;
    }

    private Map<String,UDPMessage> allMessages;
    private List<UDPMessage> allMessageList;

    private String[] receiverNames;
    private String[] commandNames;

    public Map<String,UDPMessage> getMessageMap() {
        if (allMessages == null) {
            allMessages = UDPMessage.loadMessageMap(context);
        }
        return allMessages;
    }

    public List<UDPMessage> getMessageList() {
        if (allMessageList == null) {
            allMessageList = new ArrayList<>(getMessageMap().values());
        }
        return allMessageList;
    }

    public String[] getReceiverNames() {
        if (receiverNames == null) {
            receiverNames = context.getResources().getStringArray(R.array.module_ids);
            if (receiverNames == null) {
                throw new Error("Missing redeiver ID resource");
            }
        }
        return receiverNames;
    }

    public String[] getCommandNames() {
        if (commandNames == null) {
            commandNames = context.getResources().getStringArray(R.array.pulse_cmds);
            if (commandNames == null) {
                throw new Error("Missing redeiver ID resource");
            }
        }
        return commandNames;
    }

    public String getReceiverName(int id) {
        String[] names = getReceiverNames();
        if (id == 255) {
            id =names.length - 1;
        }
        if (id < names.length) {
            return names[id];
        }
        return "Unknown-" + id;
    }

    public String getCommandName(int id) {
        String [] names = getCommandNames();
        if (id < names.length) {
            return names[id];
        }
        return "Unknwon-" + id;
    }
}
