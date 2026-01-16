# agents/langchain_based_agents/shopcore_agent.py

from langchain_core.tools import tool
from langchain.agents import create_agent
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
def shopcore_lookup(user_email: str, product_name: str) -> dict:
    """
    Fetch user, product, and latest order for a user and product.
    Uses input data for processing.
    """
    # Use input data directly
    user = input_users_db.get(user_email)
    if not user:
        return {}

    product = input_products_db.get(product_name)
    if not product:
        return {}

    # Find order for this user and product
    order = None
    for order_data in input_orders_db.values():
        if (order_data["user_email"] == user_email and 
            order_data["product_name"] == product_name):
            order = order_data
            break
    
    if not order:
        return {}

    return {
        "user_id": user["id"],
        "product_id": product["id"],
        "order_id": order["id"],
        "order_status": order["status"],
        "order_date": order["order_date"],
        "product_name": product["name"],
        "shipment_id": order.get("shipment_id"),
        "amount": order.get("amount")
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
        user = get_user_by_email(user_email)
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
        product = get_product_by_name(product_name)
        if product:
            return {
                "id": product.id,
                "name": product.name,
                "category": product.category,
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
        order = get_order_for_user_and_product(user_id, product_id)
        if order:
            return {
                "id": order.id,
                "user_id": order.user_id,
                "product_id": order.product_id,
                "order_date": str(order.order_date),
                "status": order.status
            }
        return {}

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
        tools=[shopcore_lookup, mcp_user_lookup, mcp_product_lookup, mcp_order_lookup],
        system_prompt=prompt
    )

    return agent