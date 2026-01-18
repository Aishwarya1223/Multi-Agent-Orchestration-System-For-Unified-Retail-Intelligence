# langchain_based_agents/payguard_agent.py

from __future__ import annotations

from typing import Optional

from langchain_core.tools import tool
from langchain.agents import create_agent
from asgiref.sync import sync_to_async

from omniflow.agents.langchain_based_agents.base import (
    get_llm,
    get_system_prompt,
    mcp_manager,
)

from omniflow.payguard.models import Wallet, PaymentMethod, Transaction
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
        "wallet_id": wallet.id,
        "user_id": wallet.user_id,
        "balance": str(wallet.balance),
        "currency": wallet.currency,
    }


@tool(
    description=(
        "Fetch a wallet by wallet_id. Returns all wallet fields."
    )
)
async def wallet_by_id(wallet_id: int) -> dict:
    wallet = await sync_to_async(
        lambda: Wallet.objects.using("payguard").filter(id=int(wallet_id)).first()
    )()
    if not wallet:
        return {}
    return {
        "wallet_id": wallet.id,
        "user_id": wallet.user_id,
        "balance": str(wallet.balance),
        "currency": wallet.currency,
    }


@tool(
    description=(
        "Fetch payment methods for a wallet. If wallet_id is not provided, it will look up the wallet for user_id first."
    )
)
async def payment_methods_lookup(user_id: Optional[int] = None, wallet_id: Optional[int] = None, limit: int = 20) -> dict:
    resolved_wallet_id = wallet_id
    if resolved_wallet_id is None and user_id is not None:
        wallet = await sync_to_async(
            lambda: Wallet.objects.using("payguard").filter(user_id=int(user_id)).first()
        )()
        resolved_wallet_id = wallet.id if wallet else None

    if resolved_wallet_id is None:
        return {"payment_methods": []}

    methods = await sync_to_async(
        lambda: list(
            PaymentMethod.objects.using("payguard")
            .filter(wallet_id=int(resolved_wallet_id))
            .order_by("id")[: max(1, int(limit))]
        )
    )()

    return {
        "wallet_id": int(resolved_wallet_id),
        "payment_methods": [
            {
                "method_id": m.id,
                "wallet_id": m.wallet_id,
                "provider": m.provider,
                "expiry_date": str(m.expiry_date),
            }
            for m in methods
        ],
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
                "wallet_id": tx.wallet_id,
                "order_id": tx.order_id,
                "amount": str(tx.amount),
                "type": tx.type,
                "timestamp": str(tx.timestamp),
            }
            for tx in txs
        ]
    }


@tool(
    description=(
        "Fetch transactions by wallet_id (optionally filtered by type). Returns raw transaction rows."
    )
)
async def transactions_by_wallet(wallet_id: int, tx_type: Optional[str] = None, limit: int = 50) -> dict:
    def _db_lookup():
        qs = Transaction.objects.using("payguard").filter(wallet_id=int(wallet_id))
        if tx_type:
            qs = qs.filter(type__iexact=str(tx_type).strip())
        rows = list(qs.order_by("-timestamp", "-id")[: max(1, int(limit))])
        return [
            {
                "id": t.id,
                "wallet_id": t.wallet_id,
                "order_id": t.order_id,
                "amount": str(t.amount),
                "type": t.type,
                "timestamp": str(t.timestamp),
            }
            for t in rows
        ]

    txs = await sync_to_async(_db_lookup)()
    return {"wallet_id": int(wallet_id), "transactions": txs}


@tool(
    description=(
        "Fetch a transaction by transaction_id (primary key)."
    )
)
async def transaction_by_id(transaction_id: int) -> dict:
    tx = await sync_to_async(
        lambda: Transaction.objects.using("payguard").filter(id=int(transaction_id)).first()
    )()
    if not tx:
        return {}
    return {
        "id": tx.id,
        "wallet_id": tx.wallet_id,
        "order_id": tx.order_id,
        "amount": str(tx.amount),
        "type": tx.type,
        "timestamp": str(tx.timestamp),
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
            wallet_lookup,
            wallet_by_id,
            payment_methods_lookup,
            transaction_lookup,
            transactions_by_wallet,
            transaction_by_id,
        ],
        system_prompt=prompt,
    )