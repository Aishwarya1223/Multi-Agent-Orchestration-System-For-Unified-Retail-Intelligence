#langchain_based_agents/shipstream_agent.py
from langchain_core.tools import tool
from langchain.agents import create_agent
from asgiref.sync import sync_to_async
from datetime import date
import base64
import uuid
from django.db import transaction
from django.db.utils import OperationalError

from omniflow.agents.langchain_based_agents.base import (
    get_llm,
    get_system_prompt,
    mcp_manager,
)
from omniflow.shipstream.models import Shipment, ReturnRequest, TrackingEvent, Warehouse

def normalize_tracking_id(value: str) -> str:
    return (value or "").strip().upper()

# ---------------- INTERNAL ORM ----------------

async def _shipment_lookup_internal(tracking_number: str) -> dict:
    shipment = await sync_to_async(
        lambda: Shipment.objects.using("shipstream")
        .filter(tracking_number=tracking_number)
        .first()
    )()
    if not shipment:
        return {}

    return {
        "tracking_number": shipment.tracking_number,
        "current_status": shipment.status,
        "estimated_arrival": str(shipment.estimated_arrival) if shipment.estimated_arrival else None,
        "last_updated": str(shipment.shipment_date) if shipment.shipment_date else None,
        "customer": shipment.customer_name,
        "amount": str(shipment.amount),
    }

# ---------------- TOOLS ----------------

@tool(
    description="Lookup shipment details by tracking number using Django ORM. "
                "Returns shipment status, ETA, and customer details."
)
async def shipment_lookup(query: str) -> dict:
    tracking_number = normalize_tracking_id(query)
    if not tracking_number:
        return {}
    return await _shipment_lookup_internal(tracking_number)

@tool(
    description="Lookup shipment tracking information via MCP service. "
                "Falls back to local database lookup if MCP is unavailable."
)
async def mcp_tracking_lookup(query: str) -> dict:
    tracking_number = normalize_tracking_id(query)
    try:
        result = await mcp_manager.call_tool(
            "tracking_service",
            "get_tracking",
            {"tracking_number": tracking_number},
        )
        return result.content if hasattr(result, "content") else result
    except Exception:
        return await _shipment_lookup_internal(tracking_number)


@tool(
    description=(
        "Get shipment tracking events and current location for the latest shipment "
        "associated with a given ShopCore order_id."
    )
)
async def tracking_for_order(order_id: int) -> dict:
    def _db_lookup():
        shipment = (
            Shipment.objects
            .using("shipstream")
            .filter(order_id=order_id)
            .order_by("-id")
            .first()
        )
        if not shipment:
            return {
                "found": False,
                "reason": "shipment_not_found_for_order",
                "order_id": order_id,
            }

        events = list(
            TrackingEvent.objects
            .using("shipstream")
            .filter(shipment_id=shipment.id)
            .order_by("-timestamp")[:10]
        )

        warehouse_ids = {e.warehouse_id for e in events if getattr(e, "warehouse_id", None) is not None}
        warehouses = (
            Warehouse.objects
            .using("shipstream")
            .filter(id__in=list(warehouse_ids))
        )
        warehouse_map = {w.id: w.location for w in warehouses}

        event_payload = []
        for e in events:
            event_payload.append({
                "timestamp": str(e.timestamp),
                "status_update": e.status_update,
                "warehouse_id": e.warehouse_id,
                "location": warehouse_map.get(e.warehouse_id),
            })

        current_location = None
        if event_payload:
            current_location = event_payload[0].get("location")

        return {
            "found": True,
            "order_id": order_id,
            "shipment_id": shipment.id,
            "tracking_number": shipment.tracking_number,
            "shipment_status": shipment.status,
            "current_location": current_location,
            "events": event_payload,
        }

    return await sync_to_async(_db_lookup)()


from omniflow.shipstream.models import ReverseShipment


@tool
async def check_return_status(tracking_number: str) -> dict:
    """
    Check whether a return has been created for a shipment.
    Uses MCP first, falls back to local DB.
    """

    # --------------------------------------------------
    # 1️⃣ MCP (authoritative if available)
    # --------------------------------------------------
    try:
        result = await mcp_manager.call_tool(
            "logistics_service",
            "get_return_status",
            {"tracking_number": tracking_number},
        )
        return result.content if hasattr(result, "content") else result
    except Exception:
        pass  # graceful fallback

    # --------------------------------------------------
    # 2️⃣ DB fallback (deterministic)
    # --------------------------------------------------
    reverse = await sync_to_async(
        lambda: ReverseShipment.objects
        .using("shipstream")
        .filter(original_shipment__tracking_number=tracking_number)
        .first()
    )()

    if not reverse:
        return {
            "message": (
                f"No return has been created yet for shipment {tracking_number}. "
                "The shipment is currently being processed."
            )
        }

    return {
        "message": (
            f"Yes, a return has already been created for {tracking_number}. "
            f"The return shipment {reverse.reverse_number} was initiated on "
            f"{reverse.return_date}, and the refund status is "
            f"'{reverse.refund_status}'."
        )
    }



from omniflow.shipstream.models import Shipment


@tool
async def check_return_eligibility(tracking_number: str) -> dict:
    """
    Check if a shipment is eligible for return.
    Uses MCP first, falls back to local DB.
    """

    tn = normalize_tracking_id(tracking_number)

    # --------------------------------------------------
    # 1️⃣ MCP (authoritative)
    # --------------------------------------------------
    try:
        result = await mcp_manager.call_tool(
            "logistics_service",
            "check_return_eligibility",
            {"tracking_number": tn},
        )
        payload = result.content if hasattr(result, "content") else result
        if isinstance(payload, dict) and isinstance(payload.get("eligible"), bool):
            return payload
    except Exception:
        pass

    # --------------------------------------------------
    # 2️⃣ DB fallback
    # --------------------------------------------------
    shipment = await sync_to_async(
        lambda: Shipment.objects
        .using("shipstream")
        .filter(tracking_number__iexact=tn)
        .first()
    )()

    if not shipment:
        return {
            "eligible": False,
            "message": f"I couldn't find a shipment with tracking ID {tn}."
        }

    if shipment.status != "Delivered":
        return {
            "eligible": False,
            "message": (
                f"Shipment {tn} cannot be returned because "
                f"its current status is '{shipment.status}'."
            )
        }

    return {
        "eligible": True,
        "message": (
            f"Your order {tn} was delivered successfully.\n\n"
            "Are you sure you want to initiate a return? "
            "Please reply with **YES** to confirm or **NO** to cancel."
        )
    }
@tool
async def initiate_return(tracking_number: str) -> dict:
    """
    Initiate a return for a delivered shipment.
    Uses MCP first, falls back to local DB.
    """

    # --------------------------------------------------
    # 1️⃣ MCP (authoritative path)
    # --------------------------------------------------
    try:
        result = await mcp_manager.call_tool(
            "logistics_service",
            "initiate_return",
            {"tracking_number": tracking_number},
        )
        return result.content if hasattr(result, "content") else result
    except Exception:
        pass  # graceful fallback

    # --------------------------------------------------
    # 2️⃣ DB fallback (transactional & safe)
    # --------------------------------------------------
    def _db_tx():
        tn = normalize_tracking_id(tracking_number)

        with transaction.atomic(using="shipstream"):
            shipment = (
                Shipment.objects
                .using("shipstream")
                .select_for_update()
                .filter(tracking_number__iexact=tn)
                .first()
            )

            if not shipment:
                return {
                    "success": False,
                    "message": f"I couldn't find shipment {tn}."
                }

            existing_reverse = (
                ReverseShipment.objects
                .using("shipstream")
                .filter(original_shipment=shipment)
                .first()
            )

            if existing_reverse:
                return {
                    "success": True,
                    "reverse_number": existing_reverse.reverse_number,
                    "message": (
                        f"A return has already been initiated for {tn}. "
                        f"The return shipment ID is {existing_reverse.reverse_number}."
                    )
                }

            if shipment.status != "Delivered":
                return {
                    "success": False,
                    "message": (
                        f"Shipment {tn} cannot be returned because "
                        f"its current status is '{shipment.status}'."
                    )
                }

            # 🔄 Update forward shipment
            shipment.status = "RTO_Initiated"
            shipment.save(update_fields=["status"])

            # 🔁 Create reverse shipment
            base_num = shipment.id + 9000
            reverse_number = f"REV-{base_num}"
            while (
                ReverseShipment.objects
                .using("shipstream")
                .filter(reverse_number=reverse_number)
                .exists()
            ):
                base_num += 1
                reverse_number = f"REV-{base_num}"

            reverse = ReverseShipment.objects.using("shipstream").create(
                reverse_number=reverse_number,
                original_shipment=shipment,
                return_date=date.today(),
                reason="Customer Initiated",
                refund_status="Pending",
            )

            return {
                "success": True,
                "reverse_number": reverse.reverse_number,
                "message": (
                    f"Your return has been initiated successfully for {tn}. "
                    f"The return shipment ID is {reverse.reverse_number}. "
                    "Once the item is received, your refund will be processed."
                )
            }

    return await sync_to_async(_db_tx)()


@tool(
    description=(
        "Attach a return proof image for a shipment return. "
        "Stores the base64-encoded image in the ReturnRequest table and returns a return_id."
    )
)
async def submit_return_image(tracking_number: str, user_email: str | None = None, image: str | None = None) -> dict:
    """Store a return proof image.

    Args:
        tracking_number: Forward shipment tracking number (e.g., FWD-1001).
        user_email: Optional user email associated with the return.
        image: Base64 image string or data URL (data:<mime>;base64,<data>).

    Returns:
        Dict containing success flag and return_id.
    """
    tn = normalize_tracking_id(tracking_number)
    if not tn:
        return {"success": False, "message": "Missing tracking_number."}
    if not image:
        return {"success": False, "message": "Missing image."}

    data = image
    mime = ""
    if isinstance(data, str) and data.startswith("data:") and ";base64," in data:
        header, b64 = data.split(",", 1)
        mime = header[5:].split(";", 1)[0] or ""
        data = b64

    try:
        blob = base64.b64decode(data)
    except Exception:
        return {"success": False, "message": "Invalid image encoding."}

    def _db_tx():
        try:
            with transaction.atomic(using="shipstream"):
                rr = (
                    ReturnRequest.objects
                    .using("shipstream")
                    .select_for_update()
                    .filter(tracking_number__iexact=tn, user_email=(user_email or None))
                    .first()
                )

                if not rr:
                    rr = ReturnRequest.objects.using("shipstream").create(
                        return_id=f"RET-{uuid.uuid4().hex[:10].upper()}",
                        tracking_number=tn,
                        user_email=(user_email or None),
                        status="Processed",
                    )

                rr.image_blob = blob
                rr.image_mime_type = mime or rr.image_mime_type or "image/jpeg"
                rr.status = "Processed"
                rr.save(update_fields=["image_blob", "image_mime_type", "status", "updated_at"])

                return {
                    "success": True,
                    "return_id": rr.return_id,
                    "message": f"Return processed successfully. Return ID: {rr.return_id}."
                }
        except OperationalError:
            return {
                "success": False,
                "message": (
                    "Return proof storage is not available because the ReturnRequest table "
                    "has not been migrated in the shipstream database."
                ),
            }

    return await sync_to_async(_db_tx)()

# ---------------- AGENT ----------------

def build_shipstream_agent():
    return create_agent(
        model=get_llm(),
        tools=[
            shipment_lookup,
            mcp_tracking_lookup,
            tracking_for_order,
            check_return_status,
            check_return_eligibility,
            initiate_return,
            submit_return_image,
        ],
        system_prompt=get_system_prompt("ShipStream Agent"),
    )

