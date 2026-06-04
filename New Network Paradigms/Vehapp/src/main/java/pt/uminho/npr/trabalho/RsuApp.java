package pt.uminho.npr.trabalho;

import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.AdHocModuleConfiguration;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.CamBuilder;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedAcknowledgement;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedV2xMessage;
import org.eclipse.mosaic.fed.application.app.AbstractApplication;
import org.eclipse.mosaic.fed.application.app.api.CommunicationApplication;
import org.eclipse.mosaic.fed.application.app.api.os.RoadSideUnitOperatingSystem;
import org.eclipse.mosaic.interactions.communication.V2xMessageTransmission;
import org.eclipse.mosaic.lib.geo.GeoPoint;
import org.eclipse.mosaic.lib.enums.AdHocChannel;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.lib.util.scheduling.Event;
import org.eclipse.mosaic.rti.TIME;
import java.util.HashMap;
import java.util.Optional;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Locale;

public class RsuApp extends AbstractApplication<RoadSideUnitOperatingSystem> implements CommunicationApplication {

    private static final long PERIOD = 1 * TIME.SECOND;
    private static final double RADIUS = 140.0; 
    private static final boolean ENABLE_RECOMMENDATIONS = true;
    
    private class CarData {
        double distance;
        double speed;
        public CarData(double distance, double speed) {
            this.distance = distance;
            this.speed = speed;
        }
    }

    private HashMap<String, CarData> cars_Nearby = new HashMap<>();
    private GeoPoint rsuPosition;

    @Override
    public void onStartup() {
        getLog().infoSimTime(this, "RSU started");
        getOs().getAdHocModule().enable(new AdHocModuleConfiguration()
            .addRadio().channel(AdHocChannel.CCH).power(50).distance(140).create());
        rsuPosition = GeoPoint.latLon(36.897183, -23.727146); 
        getOs().getEventManager().addEvent(new Event(getOs().getSimulationTime() + 5 * TIME.SECOND, this));
    }

    @Override
    public void onMessageReceived(ReceivedV2xMessage receivedMsg) {
        try {
            Optional<ReceivedVehInfoMessage> wrappedVehInfo = ReceivedVehInfoMessage.from(receivedMsg);
            if (wrappedVehInfo.isPresent()) {
                ReceivedVehInfoMessage receivedVehInfo = wrappedVehInfo.get();
                VehInfoMsg vehMsg = receivedVehInfo.getMessage();
                VehInfoCsvLogger.logRx(getOs().getId(), receivedVehInfo);
                // A RSU também usa lógica dinâmica para aceitar dados apenas de carros no sentido correto (90 deg)
                double diff = Math.abs(vehMsg.getHeading() - 90.0);
                if (diff <= 45.0 || diff >= 315.0) {
                    double distance_to_Car = rsuPosition.distanceTo(vehMsg.getSenderPosition());
                    double rsuLon = rsuPosition.getLongitude();
                    double carLon = vehMsg.getSenderPosition().getLongitude();
                    
                    if (distance_to_Car <= 280.0 && carLon < rsuLon) {
                        cars_Nearby.put(vehMsg.getSenderName(), new CarData(distance_to_Car, vehMsg.getSpeed()));
                        
                        // Log comentada para Debug do Multi-Hop (descomentar se o professor pedir para ver)
                        /*if (distance_to_Car > 140.0) {
                            getLog().infoSimTime(this, "[Multi-Hop Received] Data arrived from " + vehMsg.getSenderName() + 
                                " located " + String.format("%.1f", distance_to_Car) + "m away! Speed: " + 
                                String.format("%.1f", vehMsg.getSpeed()) + " m/s.");
                        }*/
                    }
                }
            }
        } catch (Exception e) {
            getLog().error("CRITICAL ERROR in onMessageReceived: " + e.getMessage());
        }
    }

    @Override public void onAcknowledgementReceived(ReceivedAcknowledgement ack) { }
    @Override
    public void onMessageTransmitted(V2xMessageTransmission tx) {
        VehInfoMessageTransmission.from(tx)
            .ifPresent(vehTx -> VehInfoCsvLogger.logTx(getOs().getId(), vehTx));
    }
    @Override public void onCamBuilding(CamBuilder camBuilder) { }

    @Override
    public void processEvent(Event event) {
        try {
            MessageRouting routing = getOs().getAdHocModule().createMessageRouting().viaChannel(AdHocChannel.CCH).topoBroadCast();

            int z1Count = 0; double z1Sum = 0;
            int z2Count = 0; double z2Sum = 0;
            int z3Count = 0; double z3Sum = 0;
            double maxStoppedDist = 0.0, minStoppedDist = Double.MAX_VALUE; 
            int stoppedCars = 0; 

            for (CarData data : cars_Nearby.values()) {
                if (data.distance <= 140.0) { z1Count++; z1Sum += data.speed; }
                else if (data.distance <= 200.0) { z2Count++; z2Sum += data.speed; }
                else if (data.distance <= 280.0) { z3Count++; z3Sum += data.speed; }

                if (data.speed < 5.0) {
                    stoppedCars++; 
                    if (data.distance > maxStoppedDist) maxStoppedDist = data.distance; 
                    if (data.distance < minStoppedDist) minStoppedDist = data.distance;
                }
            }

            double z1AvgReal = (z1Count > 0) ? z1Sum / z1Count : 35.0;
            double z2AvgReal = (z2Count > 0) ? z2Sum / z2Count : 35.0;
            double z3AvgReal = (z3Count > 0) ? z3Sum / z3Count : 35.0;
            double actualQueueLength = (stoppedCars > 1) ? maxStoppedDist - minStoppedDist : 0.0;

            double v1 = 35.0, v2 = 35.0, v3 = 35.0;
            if (ENABLE_RECOMMENDATIONS) {
                int z1Stopped = 0; int z2Stopped = 0; int z3Stopped = 0;
                for (CarData data : cars_Nearby.values()) {
                    if (data.speed < 5.0) {
                        if (data.distance <= 140.0) z1Stopped++;
                        else if (data.distance <= 200.0) z2Stopped++;
                        else if (data.distance <= 280.0) z3Stopped++;
                    }
                }

                if (z1Stopped >= 7 || (z1Count > 10 && z1AvgReal < 15.0)) {
                    v1 = 10.0; v2 = 10.0; v3 = 15.0;
                } else if (z2Stopped >= 7 || (z2Count > 8 && z2AvgReal < 20.0)) {
                    v1 = 35.0; v2 = 10.0; v3 = 15.0;
                } else if (z3Stopped >= 7 || (z3Count > 10 && z1Count < 5)) {
                    v1 = 35.0; v2 = 35.0; v3 = 15.0;
                }
            }
            
            getLog().infoSimTime(this, String.format(
                "REAL SPEEDS -> Z1:%.1f, Z2:%.1f, Z3:%.1f | CARS: Z1:%d, Z2:%d, Z3:%d | Q_Len: %.1fm | REC: V1:%.0f, V2:%.0f, V3:%.0f", 
                z1AvgReal, z2AvgReal, z3AvgReal, z1Count, z2Count, z3Count, actualQueueLength, v1, v2, v3
            ));

            // --- write metrics to scenarios/NPR/output/output.csv ---
            try {
                File out = new File("scenarios/NPR/output/output.csv");
                File parent = out.getParentFile();
                if (parent != null && !parent.exists()) parent.mkdirs();
                boolean writeHeader = !out.exists();
                try (BufferedWriter bw = new BufferedWriter(new FileWriter(out, true))) {
                    if (writeHeader) {
                        bw.write("sim_time,avg_speed,z1,z2,z3,cars_z1,cars_z2,cars_z3,total_cars,q_len_m\n");
                    }
                    double simSeconds = getOs().getSimulationTime() / (double) TIME.SECOND;
                    double avgSpeed = (z1AvgReal + z2AvgReal + z3AvgReal) / 3.0;
                    int totalCars = z1Count + z2Count + z3Count;
                    String line = String.format(Locale.US,
                        "%.3f,%.2f,%.1f,%.1f,%.1f,%d,%d,%d,%d,%.2f\n",
                        simSeconds, avgSpeed, z1AvgReal, z2AvgReal, z3AvgReal,
                        z1Count, z2Count, z3Count, totalCars, actualQueueLength
                    );
                    bw.write(line);
                }
            } catch (IOException e) {
                getLog().error("Error writing metrics CSV: " + e.getMessage());
            }

            RoadWorkMsg msg = new RoadWorkMsg(routing, rsuPosition, v1, v2, v3, RADIUS, 90.0, "rsu-" + getOs().getSimulationTime());
            getOs().getAdHocModule().sendV2xMessage(msg);

            cars_Nearby.clear();
            getOs().getEventManager().addEvent(new Event(getOs().getSimulationTime() + PERIOD, this));
        } catch (Exception e) { getLog().error("Error in processEvent: " + e.getMessage()); }
    }

    @Override public void onShutdown() { getLog().infoSimTime(this, "RSU shutdown"); }
}