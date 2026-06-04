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

public class RoadWorkMsg extends V2xMessage {
    private final EncodedPayload payload;
    private final GeoPoint eventLocation;
    private final long timestamp;
    private final double radius;
    private final String messageId;

    private final double speedNear; 
    private final double speedMid;  
    private final double speedFar; 
    
    private final double targetHeading;

    public RoadWorkMsg(MessageRouting routing, GeoPoint eventLocation, 
                       double speedNear, double speedMid, double speedFar, 
                       double radius, double targetHeading, String messageId) {
        super(routing);
        this.eventLocation = eventLocation;
        this.speedNear = speedNear;
        this.speedMid = speedMid;
        this.speedFar = speedFar;
        this.radius = radius;
        this.targetHeading = targetHeading; 
        this.timestamp = System.currentTimeMillis();
        this.messageId = messageId;

        try (ByteArrayOutputStream baos = new ByteArrayOutputStream();
             DataOutputStream dos = new DataOutputStream(baos)) {
            SerializationUtils.encodeGeoPoint(dos, eventLocation);
            dos.writeDouble(speedNear);
            dos.writeDouble(speedMid);
            dos.writeDouble(speedFar);
            dos.writeLong(timestamp);
            dos.writeDouble(radius);
            dos.writeDouble(targetHeading);
            dos.writeUTF(messageId);
            payload = new EncodedPayload(baos.toByteArray(), baos.size());
        } catch (IOException e) { throw new RuntimeException(e); }
    }

    @Nonnull @Override public EncodedPayload getPayload() { return payload; }
    public GeoPoint getEventLocation() { return eventLocation; }
    public double getSpeedNear() { return speedNear; }
    public double getSpeedMid() { return speedMid; }
    public double getSpeedFar() { return speedFar; }
    public double getRadius() { return radius; }
    public double getTargetHeading() { return targetHeading; }
    public String getMessageId() { return messageId; }
}