package pt.uminho.npr.trabalho;

import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.AdHocModuleConfiguration;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.CamBuilder;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedAcknowledgement;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedV2xMessage;
import org.eclipse.mosaic.fed.application.app.AbstractApplication;
import org.eclipse.mosaic.fed.application.app.api.CommunicationApplication;
import org.eclipse.mosaic.fed.application.app.api.VehicleApplication;
import org.eclipse.mosaic.fed.application.app.api.os.VehicleOperatingSystem;
import org.eclipse.mosaic.interactions.communication.V2xMessageTransmission;
import org.eclipse.mosaic.lib.enums.AdHocChannel;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.lib.objects.vehicle.VehicleData;
import org.eclipse.mosaic.lib.util.scheduling.Event;
import org.eclipse.mosaic.rti.TIME;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import java.util.Optional;
import org.eclipse.mosaic.lib.objects.v2x.V2xMessage;

public class VehApp extends AbstractApplication<VehicleOperatingSystem> implements VehicleApplication, CommunicationApplication
{
    private final long MsgDelay = 200 * TIME.MILLI_SECOND;
    private final int Power = 50;
    private final double Distance = 140.0;

    private double cruiseSpeed = 40.0;
    private int setVal;
    private double vehHeading;
    private double vehSpeed;
    private int vehLane;

    private org.eclipse.mosaic.lib.geo.GeoPoint last_known_Rsu = null;
    private boolean Reduced_speed = false;
    private double shortestDistanceRsu = Double.MAX_VALUE;

    private AdvancedForwarding afProtocol;
    private long nextVehInfoTime = 0; 

    @Override
    public void onShutdown() {
        getOs().getAdHocModule().disable();
    }

    @Override
    public void onStartup() {
        getOs().getAdHocModule().enable(new AdHocModuleConfiguration()
                .addRadio().channel(AdHocChannel.CCH).power(Power).distance(Distance).create());
        setVal = 0;
        afProtocol = new AdvancedForwarding(this);
        nextVehInfoTime = getOs().getSimulationTime() + MsgDelay;
        getOs().getEventManager().addEvent(nextVehInfoTime, this);
    }

    @Override
    public void processEvent(Event arg0) throws Exception {
        long currentTime = getOs().getSimulationTime();
        afProtocol.executeForwardingIfTimeReached(currentTime);

        if (currentTime == nextVehInfoTime) {
            if(setVal == 1) sendVehInfoMsg();
            nextVehInfoTime = currentTime + MsgDelay;
            getOs().getEventManager().addEvent(nextVehInfoTime, this);
        }
    }

    @Override
    public void onMessageReceived(ReceivedV2xMessage arg0) {
        V2xMessage msg = arg0.getMessage();
        Optional<ReceivedVehInfoMessage> wrappedVehInfo = ReceivedVehInfoMessage.from(arg0);

        if (msg instanceof RoadWorkMsg roadWorkMsg) {
            
            // FILTRO DINÂMICO RSU 
            double target = roadWorkMsg.getTargetHeading();
            double diff = Math.abs(this.vehHeading - target);
            if (diff > 45.0 && diff < 315.0) {
                return;
            }

            String remetente = msg.getRouting().getSource().getSourceName();
            double distanceToRsu = getOs().getPosition().distanceTo(roadWorkMsg.getEventLocation());

            // --- APLICAÇÃO DA VELOCIDADE POR ZONAS ---
            double targetSpeed;
            if (distanceToRsu <= 140.0) targetSpeed = roadWorkMsg.getSpeedNear();
            else if (distanceToRsu <= 200.0) targetSpeed = roadWorkMsg.getSpeedMid();
            else targetSpeed = roadWorkMsg.getSpeedFar();

            if (remetente.startsWith("rsu")) {
                last_known_Rsu = roadWorkMsg.getEventLocation();

                if (distanceToRsu <= roadWorkMsg.getRadius()) {
                    getLog().infoSimTime(this, "Inside Zone 1 (" + remetente + ")! Slowing down to: " + targetSpeed + " m/s.");
                    getOs().requestVehicleParametersUpdate().changeMaxSpeed(targetSpeed).apply();
                    Reduced_speed = true;
                }
                afProtocol.processOriginalMessage(roadWorkMsg, distanceToRsu);
            } 
            else if (remetente.startsWith("veh")) {
                afProtocol.processRelayedMessage(remetente);

                if (distanceToRsu > 140.0) {
                    getLog().infoSimTime(this, "In Zone 2/3! Received forwarded warning from " + remetente + " to slow down to " + targetSpeed + " m/s!");
                    last_known_Rsu = roadWorkMsg.getEventLocation();
                    getOs().requestVehicleParametersUpdate().changeMaxSpeed(targetSpeed).apply();
                    Reduced_speed = true;
                }
            }
        }
        else if (wrappedVehInfo.isPresent()) {
            ReceivedVehInfoMessage receivedVehInfo = wrappedVehInfo.get();
            VehInfoMsg vehInfoMsg = receivedVehInfo.getMessage();
            VehInfoCsvLogger.logRx(getOs().getId(), receivedVehInfo);
            // NOVO: FILTRO DINÂMICO ENTRE CARROS (V2V)
            // Agora compara o heading de quem enviou com o próprio heading do carro
            double diff = Math.abs(this.vehHeading - vehInfoMsg.getHeading());
            if (diff > 45.0 && diff < 315.0) {
                return; // Ignora se o carro não for no mesmo sentido
            }
            
            if (vehInfoMsg.getSenderName().equals(getOs().getId())) return; 

            // --- DESCOBERTA DINÂMICA DA RSU ---
            if (last_known_Rsu != null) {
                double senderDistToRsu = last_known_Rsu.distanceTo(vehInfoMsg.getSenderPosition());
                double myDistToRsu = last_known_Rsu.distanceTo(getOs().getPosition());

                if (vehInfoMsg.getHopCount() == 1) {
                    afProtocol.processRelayedVehInfo(vehInfoMsg.getSenderName());
                }
                else if (vehInfoMsg.getHopCount() == 0 && senderDistToRsu > 140.0 && myDistToRsu <= 140.0) {
                    afProtocol.processVehInfoForRelay(vehInfoMsg, myDistToRsu);
                }
            }
        }
    }

    @Override
    public void onVehicleUpdated(@Nullable VehicleData previousVehicleData, @Nonnull VehicleData updatedVehicleData) {            
        if(setVal == 0) setVal = 1;
        this.vehHeading = updatedVehicleData.getHeading().doubleValue();
        this.vehSpeed = updatedVehicleData.getSpeed();
        this.vehLane = updatedVehicleData.getRoadPosition().getLaneIndex();

        if (Reduced_speed && last_known_Rsu != null) {
            double CurrentDistance = getOs().getPosition().distanceTo(last_known_Rsu);
            if (CurrentDistance <= shortestDistanceRsu) {
                shortestDistanceRsu = CurrentDistance;
            } else if (CurrentDistance > shortestDistanceRsu + 10.0) {
                getOs().requestVehicleParametersUpdate().changeMaxSpeed(this.cruiseSpeed).apply();
                Reduced_speed = false;
                last_known_Rsu = null;
                shortestDistanceRsu = Double.MAX_VALUE; 
            }
        }
    }

    @Override
    public void onMessageTransmitted(V2xMessageTransmission arg0) {
        VehInfoMessageTransmission.from(arg0)
            .ifPresent(tx -> VehInfoCsvLogger.logTx(getOs().getId(), tx));
    }
    @Override public void onAcknowledgementReceived(ReceivedAcknowledgement arg0) { }
    @Override public void onCamBuilding(CamBuilder arg0) { }

    private void sendVehInfoMsg(){
        MessageRouting routing = getOs().getAdHocModule().createMessageRouting().viaChannel(AdHocChannel.CCH).topoBroadCast();
        
        VehInfoMsg message = new VehInfoMsg(
            routing, 
            getOs().getSimulationTime(), 
            getOs().getId(), 
            getOs().getPosition(), 
            this.vehHeading, 
            this.vehSpeed, 
            this.vehLane,
            0 
        );
        
        getOs().getAdHocModule().sendV2xMessage(message);
        
        getLog().infoSimTime(this, "Sent VehInfoMsg: " + message.toString());
    }
}