package pt.uminho.npr.trabalho;

import java.util.Optional;
import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import javax.annotation.concurrent.Immutable;
import org.eclipse.mosaic.interactions.communication.V2xMessageTransmission;
import org.eclipse.mosaic.lib.geo.GeoPoint;
import org.eclipse.mosaic.rti.api.Interaction;

@Immutable
public final class VehInfoMessageTransmission extends Interaction {

    private static final long serialVersionUID = 1L;
    public static final String TYPE_ID = createTypeIdentifier(VehInfoMessageTransmission.class);

    private final VehInfoMsg message;

    public VehInfoMessageTransmission(long time, @Nonnull VehInfoMsg message) {
        super(time);
        this.message = message;
    }

    @Nonnull
    public VehInfoMsg getMessage() {
        return message;
    }

    @Nonnull
    public String getSourceName() {
        return message.getRouting().getSource().getSourceName();
    }

    @Nullable
    public GeoPoint getSourcePosition() {
        return message.getRouting().getSource().getSourcePosition();
    }

    public int getMessageId() {
        return message.getId();
    }

    @Nonnull
    public static Optional<VehInfoMessageTransmission> from(@Nonnull V2xMessageTransmission transmission) {
        if (transmission.getMessage() instanceof VehInfoMsg vehInfoMsg) {
            return Optional.of(new VehInfoMessageTransmission(transmission.getTime(), vehInfoMsg));
        }
        return Optional.empty();
    }
}