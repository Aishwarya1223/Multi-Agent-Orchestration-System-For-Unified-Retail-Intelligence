# langchain_based_agents/payguard_agent.py

from langchain_core.tools import tool
from langchain.agents import create_agent
from omniflow.agents.langchain_based_agents.base import get_llm, get_system_prompt, mcp_manager
from omniflow.payguard.services import (
    get_wallet_by_user_id,
    get_transactions_for_order,
)
from omniflow.agents.input_data import input_payments_db
import asyncio

@tool
def payment_lookup(user_id: int, order_id: str) -> dict:
    """
    Fetch wallet and payment/refund transactions for an order.
    Uses input data for processing.
    """
    # Use input data
    mock_wallet = {
        "wallet_id": f"WAL-{user_id}",
        "balance": "5000.00",
        "currency": "INR"
    }
    
    # Find payment for this order
    payment = None
    for pay_data in input_payments_db.values():
        if pay_data["order_id"] == order_id:
            payment = pay_data
            break
    
    transactions = []
    if payment:
        transactions.append({
            "amount": str(payment["amount"]),
            "type": "payment" if payment["status"] == "Paid" else "refund",
            "status": payment["status"],
            "timestamp": "2023-10-01",
            "method": payment.get("method", "Credit Card")
        })
    
    return {
        "wallet_id": mock_wallet["wallet_id"],
        "balance": mock_wallet["balance"],
        "currency": mock_wallet["currency"],
        "transactions": transactions
    }

@tool
async def mcp_wallet_lookup(user_id: int) -> dict:
    """
    Lookup wallet information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get wallet info from MCP server
        result = await mcp_manager.call_tool("payment_service", "get_wallet", {"user_id": user_id})
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        wallet = get_wallet_by_user_id(user_id)
        if wallet:
            return {
                "id": wallet.id,
                "user_id": wallet.user_id,
                "balance": str(wallet.balance),
                "currency": wallet.currency
            }
        return {}

@tool
async def mcp_transaction_lookup(order_id: int) -> dict:
    """
    Lookup transaction information via MCP server if available.
    Falls back to local database if MCP is not available.
    """
    try:
        # Try to get transaction info from MCP server
        result = await mcp_manager.call_tool("payment_service", "get_transactions", {"order_id": order_id})
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local database
        transactions = get_transactions_for_order(order_id)
        return {
            "transactions": [
                {
                    "id": tx.id,
                    "wallet_id": tx.wallet_id,
                    "order_id": tx.order_id,
                    "amount": str(tx.amount),
                    "type": tx.type,
                    "timestamp": str(tx.timestamp)
                }
                for tx in transactions
            ]
        }

@tool
async def mcp_payment_process(wallet_id: int, order_id: int, amount: float) -> dict:
    """
    Process payment via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("payment_service", "process_payment", {
            "wallet_id": wallet_id,
            "order_id": order_id,
            "amount": amount
        })
        return result.content if hasattr(result, 'content') else result
    except Exception as e:
        return {"error": str(e)}

@tool
async def mcp_refund_process(transaction_id: int, amount: float) -> dict:
    """
    Process refund via MCP server if available.
    """
    try:
        result = await mcp_manager.call_tool("payment_service", "process_refund", {
            "transaction_id": transaction_id,
            "amount": amount
        })
        return result.content if hasattr(result, 'content') else result
    except Exception as e:
        return {"error": str(e)}

async def initialize_mcp_connections():
    """Initialize MCP connections for payguard agent"""
    # Connect to relevant MCP servers for payment operations
    await mcp_manager.connect_to_server("payment_service", ["python", "-m", "payment_mcp_server"])
    await mcp_manager.connect_to_server("fraud_service", ["python", "-m", "fraud_mcp_server"])

def build_payguard_agent():
    llm = get_llm()
    prompt = get_system_prompt("PayGuard Agent")

    # Note: MCP connections will be established when tools are first called
    # This avoids event loop issues during agent creation

    agent = create_agent(
        model=llm,
        tools=[payment_lookup, mcp_wallet_lookup, mcp_transaction_lookup, mcp_payment_process, mcp_refund_process],
        system_prompt=prompt
    )

    return agent
