package org.flg.hiromi.pulsecontroller;

import java.util.List;
import java.util.Map;

/**
 * Created by rwk on 2016-08-20.
 * A connection for managing information about {@link UDPMessage}'s and their mappings.
 */
public interface IUDPMessageContext {
    /**
     * @return a Map from tag to {@link UDPMessage}
     */
    Map<String,UDPMessage> getMessageMap();

    /**
     * @return a List of all {@link UDPMessage} defined.
     */
    List<UDPMessage> getMessageList();

    /**
     * @return A String array of all the names for the values of the receiverId field in the UDP packets
     */
    String[] getReceiverNames();

    /**
     * @return A String array of all the names of the values of the commandId field
     */
    String[] getCommandNames();

    /**
     * @param id ID from receiverId field
     * @return the name of the value
     */
    String getReceiverName(int id);

    /**
     * @param id ID from the commandId field
     * @return the name of the command
     */
    String getCommandName(int id);

    /**
     * @param tag tag name for a control
     * @return the label to use, or null if there is no override.
     */
    String getLabel(String tag);

    /**
     * Svee the {@link UDPMessage} into the local DB.
     * @param msg
     */
    void save(UDPMessage msg);

    /**
     * Restore the {@link UDPMessage to its original value.}
     * @param msg
     */
    void revert(UDPMessage msg);
}
