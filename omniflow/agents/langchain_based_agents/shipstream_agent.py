# langchain_based_agents/shipstream_agent.py

from langchain_core.tools import tool
from langchain.agents import create_agent
from omniflow.agents.langchain_based_agents.base import get_llm, get_system_prompt, mcp_manager
from omniflow.shipstream.services import (
    get_shipment_by_order_id,
    get_latest_tracking_event,
)
from omniflow.shipstream.models import Shipment, ReverseShipment, NdrEvent, ExchangeShipment
from omniflow.agents.input_data import (
    input_forward_shipments_db,
    input_reverse_shipments_db,
    input_ndr_shipments_db,
    input_exchange_shipments_db
)
import asyncio

@tool
def shipment_lookup(order_id: str = "", tracking_number: str = "") -> dict:
    """
    Fetch shipment and latest tracking status for an order.
    Uses input data for processing.
    """
    # Prefer explicit tracking_number when available
    key = (tracking_number or order_id or "").strip()
    if not key:
        return {}

    # 1) ORM-backed lookup (SQLite)
    try:
        shipment = Shipment.objects.filter(tracking_number=key).first()
        if shipment:
            # Return created?
            rev = ReverseShipment.objects.filter(original_shipment_id=shipment.tracking_number).first()
            ndr = NdrEvent.objects.filter(original_shipment_id=shipment.tracking_number).first()
            exc = ExchangeShipment.objects.filter(original_shipment_id=shipment.tracking_number).first()

            payload = {
                "tracking_number": shipment.tracking_number,
                "estimated_arrival": str(shipment.estimated_arrival) if shipment.estimated_arrival else None,
                "current_status": shipment.status,
                "last_updated": str(shipment.shipment_date) if shipment.shipment_date else None,
                "customer": shipment.customer_name,
                "amount": str(shipment.amount),
            }

            if rev:
                payload.update({
                    "return_created": True,
                    "reverse_number": rev.reverse_number,
                    "refund_status": rev.refund_status,
                    "return_reason": rev.reason,
                    "return_date": str(rev.return_date),
                })
            else:
                payload["return_created"] = False

            if ndr:
                payload.update({
                    "ndr_number": ndr.ndr_number,
                    "ndr_issue": ndr.issue,
                    "ndr_attempts": ndr.attempts,
                    "ndr_outcome": ndr.final_outcome,
                    "ndr_date": str(ndr.ndr_date),
                })

            if exc:
                payload.update({
                    "exchange_number": exc.exchange_number,
                    "exchange_status": exc.status,
                    "exchange_date": str(exc.exchange_date),
                    "new_item": exc.new_item,
                })

            return payload
    except Exception:
        # If ORM isn't ready, fall back to mock dictionaries below
        pass

    # 2) Fallback: Use input data
    shipment_data = input_forward_shipments_db.get(key)
    if shipment_data:
        return {
            "tracking_number": key,
            "estimated_arrival": "2023-10-05",
            "current_status": shipment_data["status"],
            "last_updated": shipment_data["date"],
            "customer": shipment_data["customer"],
            "amount": shipment_data["amount"]
        }
    
    # Check reverse shipments
    for rev_id, rev_data in input_reverse_shipments_db.items():
        if rev_data["original_awb"] == key:
            return {
                "tracking_number": rev_id,
                "estimated_arrival": rev_data["return_date"],
                "current_status": "Returned",
                "last_updated": rev_data["return_date"],
                "reason": rev_data["reason"],
                "refund_status": rev_data["refund_status"],
                "return_created": True,
                "reverse_number": rev_id,
            }
    
    # Check NDR shipments
    for ndr_id, ndr_data in input_ndr_shipments_db.items():
        if ndr_data["original_awb"] == key:
            return {
                "tracking_number": ndr_id,
                "estimated_arrival": ndr_data["ndr_date"],
                "current_status": f"NDR - {ndr_data['final_outcome']}",
                "last_updated": ndr_data["ndr_date"],
                "issue": ndr_data["issue"],
                "attempts": ndr_data["attempts"],
                "final_outcome": ndr_data["final_outcome"]
            }
    
    # Check exchange shipments
    for exc_id, exc_data in input_exchange_shipments_db.items():
        if exc_data["original_awb"] == key:
            return {
                "tracking_number": exc_id,
                "estimated_arrival": exc_data["exchange_date"],
                "current_status": f"Exchanged - {exc_data['status']}",
                "last_updated": exc_data["exchange_date"],
                "new_item": exc_data["new_item"],
                "exchange_status": exc_data["status"]
            }
    
    return {}

@tool
async def mcp_shipment_lookup(order_id: int) -> dict:
    """
    Lookup shipment information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get shipment info from MCP server
        result = await mcp_manager.call_tool("shipping_service", "get_shipment", {"order_id": order_id})
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        return shipment_lookup(order_id)

@tool
async def mcp_tracking_lookup(tracking_number: str) -> dict:
    """
    Lookup detailed tracking information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get detailed tracking from MCP server
        result = await mcp_manager.call_tool("tracking_service", "get_tracking", {
            "tracking_number": tracking_number
        })
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        shipment = get_shipment_by_order_id(int(tracking_number[:8]))  # Extract order ID from tracking number
        if shipment:
            latest_event = get_latest_tracking_event(shipment.id)
            return {
                "tracking_number": shipment.tracking_number,
                "estimated_arrival": str(shipment.estimated_arrival),
                "current_status": latest_event.status_update if latest_event else "Unknown",
                "last_updated": str(latest_event.timestamp) if latest_event else None,
            }
        return {}

@tool
async def mcp_warehouse_lookup(warehouse_id: int) -> dict:
    """
    Lookup warehouse information via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("warehouse_service", "get_warehouse", {"id": warehouse_id})
        return result.content if hasattr(result, 'content') else result
    except:
        return {}

async def initialize_mcp_connections():
    """Initialize MCP connections for shipstream agent"""
    # Connect to relevant MCP servers for shipping operations
    await mcp_manager.connect_to_server("shipping_service", ["python", "-m", "shipping_mcp_server"])
    await mcp_manager.connect_to_server("tracking_service", ["python", "-m", "tracking_mcp_server"])
    await mcp_manager.connect_to_server("warehouse_service", ["python", "-m", "warehouse_mcp_server"])

def build_shipstream_agent():
    llm = get_llm()
    prompt = get_system_prompt("ShipStream Agent")

    # Note: MCP connections will be established when tools are first called
    # This avoids event loop issues during agent creation

    agent = create_agent(
        model=llm,
        tools=[shipment_lookup, mcp_shipment_lookup, mcp_tracking_lookup, mcp_warehouse_lookup],
        system_prompt=prompt
    )

    return agent
