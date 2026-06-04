package pt.uminho.npr.trabalho;

import java.util.Optional;
import javax.annotation.Nonnull;
import javax.annotation.concurrent.Immutable;
import org.eclipse.mosaic.fed.application.ambassador.simulation.communication.ReceivedV2xMessage;
import org.eclipse.mosaic.lib.objects.v2x.V2xReceiverInformation;
import org.eclipse.mosaic.rti.api.Interaction;

@Immutable
public final class ReceivedVehInfoMessage extends Interaction {

    private static final long serialVersionUID = 1L;
    public static final String TYPE_ID = createTypeIdentifier(ReceivedVehInfoMessage.class);

    private final VehInfoMsg message;
    private final V2xReceiverInformation receiverInformation;

    public ReceivedVehInfoMessage(@Nonnull VehInfoMsg message, @Nonnull V2xReceiverInformation receiverInformation) {
        super(receiverInformation.getReceiveTime());
        this.message = message;
        this.receiverInformation = receiverInformation;
    }

    @Nonnull
    public VehInfoMsg getMessage() {
        return message;
    }

    @Nonnull
    public V2xReceiverInformation getReceiverInformation() {
        return receiverInformation;
    }

    @Nonnull
    public static Optional<ReceivedVehInfoMessage> from(@Nonnull ReceivedV2xMessage receivedMessage) {
        if (receivedMessage.getMessage() instanceof VehInfoMsg vehInfoMsg) {
            return Optional.of(new ReceivedVehInfoMessage(vehInfoMsg, receivedMessage.getReceiverInformation()));
        }
        return Optional.empty();
    }
}