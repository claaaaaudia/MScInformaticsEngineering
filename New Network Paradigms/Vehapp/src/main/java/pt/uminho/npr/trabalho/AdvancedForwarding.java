package pt.uminho.npr.trabalho;

import org.eclipse.mosaic.lib.enums.AdHocChannel;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.rti.TIME;
import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.util.ArrayList;

public class AdvancedForwarding {
    
    private final VehApp app;
    private RoadWorkMsg msgToForward = null;
    private long exactForwardingTime = -1;

    private HashMap<String, Long> pendingVehInfoRelays = new HashMap<>();
    private HashMap<String, VehInfoMsg> pendingVehMsgs = new HashMap<>();

    public AdvancedForwarding(VehApp app) {
        this.app = app;
    }

    public void processOriginalMessage(RoadWorkMsg msg, double distanceToRsu) {
        if (distanceToRsu <= 140.0) {
            long delayMs = (long) ((140.0 - distanceToRsu) * 10);
            this.msgToForward = msg;
            this.exactForwardingTime = app.getOs().getSimulationTime() + delayMs * TIME.MILLI_SECOND;
            app.getOs().getEventManager().addEvent(this.exactForwardingTime, app);
        }
    }

    public void processRelayedMessage(String remetente) {
        if (this.msgToForward != null) {
            // Log clara: Cancelou a mensagem de DOWNLINK (RSU -> Veículos)
            app.getLog().infoSimTime(app, "[AF DOWNLINK] Heard " + remetente + " relaying RSU Warning! Canceled my timer.");
            this.msgToForward = null; 
        }
    }

    public void processVehInfoForRelay(VehInfoMsg msg, double myDistToRsu) {
        String origSender = msg.getSenderName();
        if (!pendingVehInfoRelays.containsKey(origSender)) {
            long delayMs = (long) (myDistToRsu * 5);
            long fireTime = app.getOs().getSimulationTime() + delayMs * TIME.MILLI_SECOND;
            
            pendingVehInfoRelays.put(origSender, fireTime);
            pendingVehMsgs.put(origSender, msg);
            app.getOs().getEventManager().addEvent(fireTime, app);
        }
    }

    public void processRelayedVehInfo(String origSender) {
        if (pendingVehInfoRelays.containsKey(origSender)) {
            pendingVehInfoRelays.remove(origSender);
            pendingVehMsgs.remove(origSender);
            // Log clara: Cancelou a mensagem de UPLINK (Veículo -> RSU)
            app.getLog().infoSimTime(app, "[AF UPLINK] Heard someone else relaying data for " + origSender + "! Canceled my timer to RSU.");
        }
    }

    public void executeForwardingIfTimeReached(long currentSimulationTime) {
        
        // --- SENTIDO: RSU -> VEÍCULOS (DOWNLINK) ---
        if (this.msgToForward != null && currentSimulationTime == this.exactForwardingTime) {
            MessageRouting routing = app.getOs().getAdHocModule().createMessageRouting().viaChannel(AdHocChannel.CCH).topoBroadCast();
            RoadWorkMsg relayMsg = new RoadWorkMsg(
                routing, 
                this.msgToForward.getEventLocation(), 
                this.msgToForward.getSpeedNear(), 
                this.msgToForward.getSpeedMid(), 
                this.msgToForward.getSpeedFar(), 
                this.msgToForward.getRadius(),
                this.msgToForward.getTargetHeading(), 
                this.msgToForward.getMessageId()
            );
            app.getOs().getAdHocModule().sendV2xMessage(relayMsg);
            
            // Log de quem fez o envio DOWNLINK
            app.getLog().infoSimTime(app, "[AF DOWNLINK] I am the chosen relay! Forwarding RSU Warning to vehicles in the back!");
            
            this.msgToForward = null; 
        }

        // --- SENTIDO: VEÍCULOS -> RSU (UPLINK) ---
        List<String> toRemove = new ArrayList<>();
        for (Map.Entry<String, Long> entry : pendingVehInfoRelays.entrySet()) {
            if (entry.getValue() == currentSimulationTime) {
                String origSender = entry.getKey();
                VehInfoMsg origMsg = pendingVehMsgs.get(origSender);

                MessageRouting routing = app.getOs().getAdHocModule().createMessageRouting().viaChannel(AdHocChannel.CCH).topoBroadCast();
                
                VehInfoMsg relayMsg = new VehInfoMsg(
                    routing, origMsg.getTimeStamp(), origMsg.getSenderName(),
                    origMsg.getSenderPosition(), origMsg.getHeading(), origMsg.getSpeed(),
                    origMsg.getLaneId(), origMsg.getHopCount() + 1
                );
                
                app.getOs().getAdHocModule().sendV2xMessage(relayMsg);
                
                // Log de quem fez o envio UPLINK
                app.getLog().infoSimTime(app, "[AF UPLINK] I am the chosen relay! Forwarding Data from " + origSender + " to the RSU!");
                
                toRemove.add(origSender);
            }
        }
        for (String s : toRemove) {
            pendingVehInfoRelays.remove(s);
            pendingVehMsgs.remove(s);
        }
    }
}