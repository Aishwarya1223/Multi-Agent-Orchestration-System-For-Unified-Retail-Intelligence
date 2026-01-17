#langchain_based_agents/shipstream_agent.py
from langchain_core.tools import tool
from langchain.agents import create_agent
from asgiref.sync import sync_to_async
from datetime import date
from django.db import transaction

from omniflow.agents.langchain_based_agents.base import (
    get_llm,
    get_system_prompt,
    mcp_manager,
)
from omniflow.shipstream.models import Shipment

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

# ---------------- AGENT ----------------

def build_shipstream_agent():
    return create_agent(
        model=get_llm(),
        tools=[
            shipment_lookup,
            mcp_tracking_lookup,
            check_return_status,
            check_return_eligibility,
            initiate_return,
        ],
        system_prompt=get_system_prompt("ShipStream Agent"),
    )

