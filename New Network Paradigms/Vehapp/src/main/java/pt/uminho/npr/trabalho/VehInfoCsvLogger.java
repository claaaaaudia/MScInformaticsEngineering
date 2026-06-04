package pt.uminho.npr.trabalho;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Locale;

public final class VehInfoCsvLogger {

    private static final String OUTPUT_PATH = "scenarios/NPR/output/vehinfo_output.csv";
    private static final Object LOCK = new Object();

    private VehInfoCsvLogger() {
    }

    public static void logTx(String observerNode, VehInfoMessageTransmission tx) {
        VehInfoMsg msg = tx.getMessage();
        writeLine(
            "TX",
            tx.getTime(),
            observerNode,
            msg,
            "",
            ""
        );
    }

    public static void logRx(String observerNode, ReceivedVehInfoMessage rx) {
        VehInfoMsg msg = rx.getMessage();
        writeLine(
            "RX",
            rx.getTime(),
            observerNode,
            msg,
            observerNode,
            Long.toString(rx.getReceiverInformation().getReceiveTime())
        );
    }

    private static void writeLine(
        String direction,
        long simTime,
        String observerNode,
        VehInfoMsg msg,
        String receiverName,
        String receiveTime
    ) {
        synchronized (LOCK) {
            File out = new File(OUTPUT_PATH);
            File parent = out.getParentFile();
            if (parent != null && !parent.exists()) {
                parent.mkdirs();
            }

            boolean writeHeader = !out.exists() || out.length() == 0;

            try (BufferedWriter bw = new BufferedWriter(new FileWriter(out, true))) {
                if (writeHeader) {
                    bw.write("direction,sim_time_ns,observer_node,msg_id,sender_name,sender_lat,sender_lon,heading_deg,speed_mps,lane_id,hop_count,receiver_name,receiver_time_ns\n");
                }

                String line = String.format(
                    Locale.US,
                    "%s,%d,%s,%d,%s,%.8f,%.8f,%.2f,%.3f,%d,%d,%s,%s\n",
                    direction,
                    simTime,
                    safe(observerNode),
                    msg.getId(),
                    safe(msg.getSenderName()),
                    msg.getSenderPosition().getLatitude(),
                    msg.getSenderPosition().getLongitude(),
                    msg.getHeading(),
                    msg.getSpeed(),
                    msg.getLaneId(),
                    msg.getHopCount(),
                    safe(receiverName),
                    safe(receiveTime)
                );
                bw.write(line);
            } catch (IOException ignored) {
                // Keep simulation running if filesystem logging fails.
            }
        }
    }

    private static String safe(String value) {
        if (value == null) {
            return "";
        }
        return value.replace(',', '_');
    }
}