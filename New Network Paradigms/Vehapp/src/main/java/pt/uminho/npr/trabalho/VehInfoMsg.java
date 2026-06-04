package pt.uminho.npr.trabalho;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import javax.annotation.Nonnull;
import org.eclipse.mosaic.lib.geo.GeoPoint;
import org.eclipse.mosaic.lib.objects.v2x.EncodedPayload;
import org.eclipse.mosaic.lib.objects.v2x.MessageRouting;
import org.eclipse.mosaic.lib.objects.v2x.V2xMessage;
import org.eclipse.mosaic.lib.util.SerializationUtils;

public class VehInfoMsg extends V2xMessage {
    
    private final EncodedPayload payload;
    private final long timeStamp;
    private final String senderName;
    private final GeoPoint senderPos;
    private final double senderHeading;
    private final double senderSpeed;
    private final int senderLaneId;
    
    private final int hopCount; 

    public VehInfoMsg(
        final MessageRouting routing,
        final long time,
        final String name,
        final GeoPoint pos,
        final double heading,
        final double speed,
        final int laneId,
        final int hopCount) {

        super(routing);
        this.timeStamp = time;
        this.senderName = name;
        this.senderPos = pos;
        this.senderHeading = heading;
        this.senderSpeed = speed;
        this.senderLaneId = laneId;
        this.hopCount = hopCount; 

        try (final ByteArrayOutputStream baos = new ByteArrayOutputStream();
             final DataOutputStream dos = new DataOutputStream(baos)) {
            dos.writeLong(timeStamp);
            dos.writeUTF(senderName);
            SerializationUtils.encodeGeoPoint(dos, senderPos);
            dos.writeDouble(senderHeading);
            dos.writeDouble(senderSpeed);
            dos.writeInt(senderLaneId);
            dos.writeInt(hopCount); // <--- Adicionado aqui na serialização

            payload = new EncodedPayload(baos.toByteArray(), baos.size());
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    @Nonnull
    @Override
    public EncodedPayload getPayload() {
        return payload;
    }

    public long getTimeStamp() {
        return timeStamp;
    }

    public String getSenderName() {
        return senderName;
    }

    public GeoPoint getSenderPosition() {
        return senderPos;
    }
    
    public double getHeading() {
        return senderHeading;
    }

    public double getSpeed() {
        return senderSpeed;
    }

    public int getLaneId() {
        return senderLaneId;
    }

    public int getHopCount() {
        return hopCount;
    }

    @Override
    public String toString() {
        return "VehInfoMessage{" + 
            "timeStamp=" + timeStamp + 
            ", senderName=" + senderName + 
            ", senderPosition=" + senderPos + 
            ", senderHeading=" + senderHeading + 
            ", senderSpeed=" + senderSpeed + 
            ", senderLaneId=" + senderLaneId +
            ", hopCount=" + hopCount + '}';
    }
}