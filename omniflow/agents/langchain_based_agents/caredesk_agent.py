# langchain_based_agents/caredesk_agent.py

from typing import Optional

from langchain_core.tools import tool
from langchain.agents import create_agent
from omniflow.agents.langchain_based_agents.base import get_llm, get_system_prompt, mcp_manager
from omniflow.caredesk.services import (
    get_latest_ticket_for_user,
    get_messages_for_ticket,
)
from omniflow.agents.input_data import input_tickets_db
import asyncio
from asgiref.sync import sync_to_async

from omniflow.caredesk.models import Ticket, TicketMessage


@tool(
    description="Automatically create a support ticket for refund processing."
)
async def auto_create_refund_ticket(
    user_id: int,
    order_id: int,
    tracking_number: str,
    refund_status: str,
) -> dict:
    """
    Creates a CareDesk ticket automatically after refund initiation.
    """

    ticket = await sync_to_async(Ticket.objects.create)(
        user_id=user_id,
        reference_id=order_id,
        issue_type="Refund Request",
    )

    await sync_to_async(TicketMessage.objects.create)(
        ticket=ticket,
        sender="Agent",
        content=(
            f"A refund has been initiated for shipment {tracking_number}. "
            f"Current refund status: {refund_status}."
        ),
    )

    return {
        "ticket_id": ticket.id,
        "message": (
            "A support ticket has been automatically created "
            "to track your refund."
        ),
    }


@tool(
    description=(
        "Fetch the latest support ticket status for a user. "
        "Optionally scope the lookup to a specific order_id (stored as Ticket.reference_id)."
    )
)
async def latest_ticket_status(user_id: int, order_id: Optional[int] = None) -> dict:
    order_ref = str(order_id) if order_id is not None else None

    def _db_lookup():
        qs = Ticket.objects.using("caredesk").filter(user_id=user_id)
        if order_ref:
            qs = qs.filter(reference_id=order_ref)
        t = qs.order_by("-created_at", "-id").first()
        if not t:
            return {
                "found": False,
                "reason": "ticket_not_found",
                "user_id": user_id,
                "order_id": order_id,
            }

        status = (t.status or "").strip()
        status_key = status.lower().replace("-", " ").replace("_", " ").strip()
        assigned = status_key in {"assigned", "in progress", "inprogress"}

        return {
            "found": True,
            "ticket_id": t.id,
            "status": status,
            "issue_type": t.issue_type,
            "created_at": str(t.created_at),
            "reference_id": t.reference_id,
            "assigned": assigned,
        }

    return await sync_to_async(_db_lookup)()

@tool
def ticket_lookup(user_id: int) -> dict:
    """
    Fetch latest support ticket and messages for a user.
    Uses input data for processing.
    """
    # Use input data - find ticket for this user
    for ticket_data in input_tickets_db.values():
        if ticket_data["user_id"] == user_id:
            return {
                "ticket_id": "TKT-1001" if user_id == 1 else "TKT-1002",
                "issue_type": ticket_data["subject"],
                "status": ticket_data["status"],
                "created_at": ticket_data["created_date"],
                "messages": [
                    {
                        "sender": "customer",
                        "content": f"I need help with my order - {ticket_data['subject']}",
                        "timestamp": ticket_data["created_date"]
                    },
                    {
                        "sender": "support",
                        "content": f"Your ticket regarding {ticket_data['subject']} is {ticket_data['status'].lower()}",
                        "timestamp": ticket_data["created_date"]
                    }
                ]
            }
    
    return {}

@tool
async def mcp_ticket_lookup(user_id: int) -> dict:
    """
    Lookup ticket information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get ticket info from MCP server
        result = await mcp_manager.call_tool("support_service", "get_ticket", {"user_id": user_id})
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        return ticket_lookup(user_id)

@tool
async def mcp_create_ticket(user_id: int, issue_type: str, description: str) -> dict:
    """
    Create a new support ticket via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("support_service", "create_ticket", {
            "user_id": user_id,
            "issue_type": issue_type,
            "description": description
        })
        return result.content if hasattr(result, 'content') else result
    except Exception as e:
        return {"error": str(e)}

@tool
async def mcp_add_message(ticket_id: int, sender: str, content: str) -> dict:
    """
    Add a message to a support ticket via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("support_service", "add_message", {
            "ticket_id": ticket_id,
            "sender": sender,
            "content": content
        })
        return result.content if hasattr(result, 'content') else result
    except Exception as e:
        return {"error": str(e)}

@tool
async def mcp_escalate_ticket(ticket_id: int, reason: str) -> dict:
    """
    Escalate a support ticket via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("support_service", "escalate_ticket", {
            "ticket_id": ticket_id,
            "reason": reason
        })
        return result.content if hasattr(result, 'content') else result
    except Exception as e:
        return {"error": str(e)}

@tool
async def mcp_knowledge_base_search(query: str) -> dict:
    """
    Search knowledge base via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("knowledge_service", "search", {"query": query})
        return result.content if hasattr(result, 'content') else result
    except Exception as e:
        return {"error": str(e)}

async def initialize_mcp_connections():
    """Initialize MCP connections for caredesk agent"""
    # Connect to relevant MCP servers for customer support operations
    await mcp_manager.connect_to_server("support_service", ["python", "-m", "support_mcp_server"])
    await mcp_manager.connect_to_server("knowledge_service", ["python", "-m", "knowledge_mcp_server"])
    await mcp_manager.connect_to_server("notification_service", ["python", "-m", "notification_mcp_server"])

def build_caredesk_agent():
    llm = get_llm()
    prompt = get_system_prompt("CareDesk Agent")

    # Note: MCP connections will be established when tools are first called
    # This avoids event loop issues during agent creation

    agent = create_agent(
        model=llm,
        tools=[ticket_lookup, 
               mcp_ticket_lookup, 
               mcp_create_ticket, 
               mcp_add_message, 
               mcp_escalate_ticket, 
               mcp_knowledge_base_search,
               auto_create_refund_ticket,
               latest_ticket_status,],
        system_prompt=prompt
    )

    return agent
