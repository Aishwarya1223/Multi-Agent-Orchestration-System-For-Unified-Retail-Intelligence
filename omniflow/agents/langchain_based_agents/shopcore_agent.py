# agents/langchain_based_agents/shopcore_agent.py

from langchain_core.tools import tool
from langchain.agents import create_agent
from asgiref.sync import sync_to_async
from omniflow.agents.langchain_based_agents.base import get_llm, get_system_prompt, mcp_manager

from omniflow.shopcore.services import (
    get_user_by_email,
    get_product_by_name,
    get_order_for_user_and_product,
)
from omniflow.agents.input_data import (
    input_users_db,
    input_products_db,
    input_orders_db
)
import asyncio

@tool
async def resolve_user_identity(user_email: str) -> dict:
    """
    Resolve and verify user identity.
    """
    try:
        result = await mcp_manager.call_tool(
            "user_service",
            "get_user",
            {"email": user_email}
        )
        return result.content if hasattr(result, "content") else result
    except:
        user = await sync_to_async(lambda: get_user_by_email(user_email))()
        if not user:
            return {}
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "premium_status": user.premium_status,
        }


@tool
async def mcp_user_lookup(user_email: str) -> dict:
    """
    Lookup user information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get user info from MCP server
        result = await mcp_manager.call_tool("user_service", "get_user", {"email": user_email})
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        user = await sync_to_async(lambda: get_user_by_email(user_email))()
        if user:
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "premium_status": user.premium_status
            }
        return {}

@tool
async def mcp_product_lookup(product_name: str) -> dict:
    """
    Lookup product information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get product info from MCP server
        result = await mcp_manager.call_tool("product_service", "get_product", {"name": product_name})
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        product = await sync_to_async(lambda: get_product_by_name(product_name))()
        if product:
            return {
                "id": product.id,
                "name": product.name,
                "price": str(product.price)
            }
        return {}

@tool
async def mcp_order_lookup(user_id: int, product_id: int) -> dict:
    """
    Lookup order information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get order info from MCP server
        result = await mcp_manager.call_tool("order_service", "get_order", {
            "user_id": user_id,
            "product_id": product_id
        })
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        order = await sync_to_async(lambda: get_order_for_user_and_product(user_id, product_id))()
        if order:
            return {
                "id": order.id,
                "user_id": order.user_id,
                "product_id": order.product_id,
                "order_date": str(order.order_date),
                "status": order.status
            }
        return {}

@tool(
    description=(
        "Verify that an order belongs to the user identified by email. "
        "Returns ownership status without exposing order details."
    )
)
async def verify_order_ownership(order_id: int, user_email: str) -> dict:
    from omniflow.shopcore.models import Order, User
    from asgiref.sync import sync_to_async

    user_email = (user_email or "").strip().lower()
    if not user_email:
        return {"valid": False, "reason": "missing_user_email"}

    user = await sync_to_async(
        lambda: User.objects.using("shopcore")
        .filter(email__iexact=user_email)
        .first()
    )()

    if not user:
        return {"valid": False, "reason": "user_not_found"}

    order = await sync_to_async(
        lambda: Order.objects.using("shopcore")
        .filter(id=order_id, user_id=user.id)
        .first()
    )()

    if not order:
        return {"valid": False, "reason": "ownership_mismatch"}

    return {
        "valid": True,
        "order_id": order.id,
        "user_id": user.id,
    }

@tool(
    description=(
        "Resolve the latest order for a given user (by email) and product name. "
        "Returns user_id, product_id, and order_id if found."
    )
)
async def lookup_order_for_user_product(user_email: str, product_name: str) -> dict:
    user_email = (user_email or "").strip().lower()
    product_name = (product_name or "").strip()

    if not user_email or not product_name:
        return {"found": False, "reason": "missing_user_or_product"}

    from omniflow.shopcore.models import User, Product, Order

    user = await sync_to_async(
        lambda: User.objects.using("shopcore").filter(email__iexact=user_email).first()
    )()
    if not user:
        return {"found": False, "reason": "user_not_found"}

    product = await sync_to_async(
        lambda: Product.objects.using("shopcore")
        .filter(name__icontains=product_name)
        .order_by("id")
        .first()
    )()
    if not product:
        return {"found": False, "reason": "product_not_found", "user_id": user.id}

    order = await sync_to_async(
        lambda: Order.objects.using("shopcore")
        .filter(user_id=user.id, product_id=product.id)
        .order_by("-order_date", "-id")
        .first()
    )()
    if not order:
        return {
            "found": False,
            "reason": "order_not_found",
            "user_id": user.id,
            "product_id": product.id,
        }

    return {
        "found": True,
        "user_id": user.id,
        "product_id": product.id,
        "product_name": product.name,
        "order_id": order.id,
        "order_date": str(order.order_date),
        "order_status": order.status,
    }

async def initialize_mcp_connections():
    """Initialize MCP connections for shopcore agent"""
    # Connect to relevant MCP servers for shopcore operations
    await mcp_manager.connect_to_server("user_service", ["python", "-m", "user_mcp_server"])
    await mcp_manager.connect_to_server("product_service", ["python", "-m", "product_mcp_server"])
    await mcp_manager.connect_to_server("order_service", ["python", "-m", "order_mcp_server"])

def build_shopcore_agent():
    llm = get_llm()
    prompt = get_system_prompt("ShopCore Agent")

    # Note: MCP connections will be established when tools are first called
    # This avoids event loop issues during agent creation

    agent = create_agent(
        model=llm,
        tools=[
            resolve_user_identity,
            mcp_user_lookup,
            mcp_product_lookup,
            mcp_order_lookup,
            verify_order_ownership,
            lookup_order_for_user_product,
        ],
        system_prompt=prompt
    )


    return agent