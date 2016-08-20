package org.flg.hiromi.pulsecontroller;

import android.app.Service;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.sqlite.SQLiteDatabase;
import android.os.Binder;
import android.os.IBinder;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.flg.hiromi.pulsecontroller.UDPMessage.FIELD_COMMAND;
import static org.flg.hiromi.pulsecontroller.UDPMessage.FIELD_DATA;
import static org.flg.hiromi.pulsecontroller.UDPMessage.FIELD_RECEIVER;
import static org.flg.hiromi.pulsecontroller.UDPMessage.FIELD_TAG;
import static org.flg.hiromi.pulsecontroller.UDPMessage.FIELD_TYPE;
import static org.flg.hiromi.pulsecontroller.UDPMessage.TABLE_NAME;

public class UDPMessageDataService extends Service {
    public UDPMessageDataService() {
    }

    @Override
    public IBinder onBind(Intent intent) {
        return new UDPMessageContext(this);
    }

    /**
     * Wraps a {@link Context} object and caches the UDPMessage data
     */

    public static class UDPMessageContext extends Binder implements IUDPMessageContext {
        private final Context context;
        public UDPMessageContext(Context ctx) {
            context = ctx;
        }

        private Map<String,UDPMessage> allMessages;
        private List<UDPMessage> allMessageList;

        private String[] receiverNames;
        private String[] commandNames;

        private UDPMessageDBHelper opener;

        @Override
        public Map<String,UDPMessage> getMessageMap() {
            if (allMessages == null) {
                allMessages = UDPMessage.loadMessageMap(context);
            }
            return allMessages;
        }

        @Override
        public List<UDPMessage> getMessageList() {
            if (allMessageList == null) {
                allMessageList = new ArrayList<>(getMessageMap().values());
            }
            return allMessageList;
        }

        @Override
        public String[] getReceiverNames() {
            if (receiverNames == null) {
                receiverNames = context.getResources().getStringArray(R.array.module_ids);
                if (receiverNames == null) {
                    throw new Error("Missing redeiver ID resource");
                }
            }
            return receiverNames;
        }

        @Override
        public String[] getCommandNames() {
            if (commandNames == null) {
                commandNames = context.getResources().getStringArray(R.array.pulse_cmds);
                if (commandNames == null) {
                    throw new Error("Missing redeiver ID resource");
                }
            }
            return commandNames;
        }

        @Override
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

        @Override
        public String getCommandName(int id) {
            String [] names = getCommandNames();
            if (id < names.length) {
                return names[id];
            }
            return "Unknwon-" + id;
        }

        private UDPMessageDBHelper getDBHelper() {
            if (opener == null) {
                opener = new UDPMessageDBHelper(context);
            }
            return opener;
        }

        @Override
        public void save(UDPMessage msg) {
            // If we're back to the original, just clean up, so we pick up future changes.
            if (!msg.isOverride()) {
                revert(msg);
            } else {
                try (SQLiteDatabase db = getDBHelper().getWritableDatabase()) {
                    ContentValues values = new ContentValues();
                    values.put(FIELD_TAG, msg.getTag());
                    values.put(FIELD_TYPE, msg.getType());
                    values.put(FIELD_RECEIVER, msg.getReceiverId());
                    values.put(FIELD_COMMAND, msg.getCommandId());
                    if (!msg.getNeedsData()) {
                        values.put(FIELD_DATA, msg.getData());
                    }
                    db.insertWithOnConflict(TABLE_NAME, null, values, SQLiteDatabase.CONFLICT_REPLACE);
                }
            }
        }

        @Override
        public void revert(UDPMessage msg) {
            msg.revert();
            try (SQLiteDatabase db = getDBHelper().getWritableDatabase()) {
                db.delete(TABLE_NAME, "tag=?", new String[] { msg.getTag() });
            }
        }
    }
}
