from shipstream.services import (
    get_shipment_by_order_id,
    get_latest_tracking_event,
)


def shipstream_agent(order_id: int):
    """
    Fetches shipment and latest tracking status for an order.
    """

    shipment = get_shipment_by_order_id(order_id)
    if not shipment:
        return None

    latest_event = get_latest_tracking_event(shipment.id)

    return {
        "tracking_number": shipment.tracking_number,
        "estimated_arrival": str(shipment.estimated_arrival),
        "current_status": latest_event.status_update if latest_event else "Status unavailable",
        "last_updated": str(latest_event.timestamp) if latest_event else None,
    }
