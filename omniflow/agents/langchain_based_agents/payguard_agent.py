# langchain_based_agents/payguard_agent.py

from langchain_core.tools import tool
from langchain.agents import create_agent
from asgiref.sync import sync_to_async

from omniflow.agents.langchain_based_agents.base import (
    get_llm,
    get_system_prompt,
    mcp_manager,
)

from omniflow.payguard.models import Wallet
from omniflow.payguard.services import get_transactions_for_order

# --------------------------------------------------
# WALLET LOOKUP (MCP → DB FALLBACK)
# --------------------------------------------------

@tool(
    description=(
        "Fetch wallet balance for a user. Wallets are user-scoped and "
        "are NOT linked to shipment or tracking IDs."
    )
)
async def wallet_lookup(user_id: int) -> dict:
    """
    Wallet lookup using MCP first, then DB fallback.
    """

    # ---------- MCP (authoritative if available) ----------
    try:
        result = await mcp_manager.call_tool(
            "payment_service",
            "get_wallet",
            {"user_id": user_id},
        )
        return result.content if hasattr(result, "content") else result
    except Exception:
        pass

    # ---------- DB fallback (deterministic) ----------
    wallet = await sync_to_async(
        lambda: Wallet.objects.filter(user_id=user_id).first()
    )()

    if not wallet:
        return {}

    return {
        "user_id": wallet.user_id,
        "balance": str(wallet.balance),
        "currency": wallet.currency,
    }


# --------------------------------------------------
# TRANSACTIONS (OPTIONAL, ORDER-SCOPED)
# --------------------------------------------------

@tool(
    description=(
        "Fetch wallet transactions for a specific order ID. "
        "Only valid when an order_id is already verified by ShopCore."
    )
)
async def transaction_lookup(order_id: int) -> dict:
    """
    Transaction lookup via MCP with DB fallback.
    """

    # ---------- MCP ----------
    try:
        result = await mcp_manager.call_tool(
            "payment_service",
            "get_transactions",
            {"order_id": order_id},
        )
        return result.content if hasattr(result, "content") else result
    except Exception:
        pass

    # ---------- DB fallback ----------
    txs = await sync_to_async(
        lambda: list(get_transactions_for_order(order_id))
    )()

    return {
        "transactions": [
            {
                "id": tx.id,
                "order_id": tx.order_id,
                "amount": str(tx.amount),
                "type": tx.type,
                "timestamp": str(tx.timestamp),
            }
            for tx in txs
        ]
    }


# --------------------------------------------------
# AGENT BUILDER
# --------------------------------------------------

def build_payguard_agent():
    llm = get_llm()
    prompt = get_system_prompt("PayGuard Agent")

    return create_agent(
        model=llm,
        tools=[
            wallet_lookup,        # PRIMARY
            transaction_lookup,   # OPTIONAL (order-scoped)
        ],
        system_prompt=prompt,
    )