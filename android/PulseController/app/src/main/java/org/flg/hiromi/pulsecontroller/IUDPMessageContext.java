package org.flg.hiromi.pulsecontroller;

import java.util.List;
import java.util.Map;

/**
 * Created by rwk on 2016-08-20.
 */
public interface IUDPMessageContext {
    Map<String,UDPMessage> getMessageMap();

    List<UDPMessage> getMessageList();

    String[] getReceiverNames();

    String[] getCommandNames();

    String getReceiverName(int id);

    String getCommandName(int id);

    void save(UDPMessage msg);

    void revert(UDPMessage msg);
}
