from .models import Shipment, TrackingEvent


def get_shipment_by_order_id(order_id: int):
    return Shipment.objects.filter(order_id=order_id).first()


def get_latest_tracking_event(shipment_id: int):
    return (
        TrackingEvent.objects
        .filter(shipment_id=shipment_id)
        .order_by("-timestamp")
        .first()
    )
