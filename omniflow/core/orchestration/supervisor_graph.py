#core/orchestration/supervisor_graph.py
from typing import TypedDict, Optional, Dict, Any, List
from dataclasses import dataclass
import os
import re
import json

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django
django.setup()

from asgiref.sync import sync_to_async
from django.db import connections

from omniflow.utils.logging import get_logger
from omniflow.utils.prompts import get_response_synthesizer_prompt
from omniflow.utils.config import settings as pydantic_settings

from omniflow.agents.langchain_based_agents.shopcore_agent import (
    build_shopcore_agent,
    lookup_order_for_user_product,
)
from omniflow.agents.langchain_based_agents.shipstream_agent import (
    build_shipstream_agent,
    check_return_eligibility,
    check_return_status,
    initiate_return,
    submit_return_image,
    tracking_for_order,
)
from omniflow.agents.langchain_based_agents.payguard_agent import build_payguard_agent
from omniflow.agents.langchain_based_agents.caredesk_agent import (
    build_caredesk_agent,
    latest_ticket_status,
)

from omniflow.shipstream.models import Shipment, ReverseShipment, NdrEvent, ExchangeShipment
from omniflow.shopcore.models import Order, User, Product
from omniflow.payguard.models import Transaction

logger = get_logger(__name__)

# -------------------------------------------------------------------
# LLM (response synthesis only)
# -------------------------------------------------------------------

RESPONSE_SYNTH_LLM = ChatOpenAI(
    temperature=0,
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    api_key=pydantic_settings.OPENAI_API_KEY,
    timeout=15,
    max_retries=1,
)


def _is_yes(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(re.match(r"^(yes|y|yeah|yep|confirm|confirmed|sure|ok|okay)$", t))


def _is_no(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(re.match(r"^(no|n|nope|cancel|cancelled)$", t))


def _synthesize_answer(user_message: str, facts: Dict[str, Any]) -> str:
    prompt = get_response_synthesizer_prompt()
    msg = (
        "USER_MESSAGE:\n"
        f"{user_message}\n\n"
        "FACTS_JSON:\n"
        f"{json.dumps(facts, ensure_ascii=False)}"
    )
    out = RESPONSE_SYNTH_LLM.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=msg),
    ])
    return (getattr(out, "content", "") or "").strip()

# -------------------------------------------------------------------
# Supervisor State
# -------------------------------------------------------------------

class SupervisorState(TypedDict):
    query: str
    user_email: str
    user_name: Optional[str]
    image: Optional[str]
    reference_id: Optional[str]

    intent: Optional[str]
    pending_action: Optional[Dict[str, Any]]

    shopcore_ctx: Optional[Dict[str, Any]]
    shipstream_ctx: Optional[Dict[str, Any]]
    payguard_ctx: Optional[Dict[str, Any]]
    caredesk_ctx: Optional[Dict[str, Any]]

    facts: Optional[Dict[str, Any]]
    decision_trace: list
    confidence_score: float
    final_response: Optional[str]




def intent_gate(state: SupervisorState) -> SupervisorState:
    raw_q = state.get("query") or ""
    q = raw_q.lower()

    if state.get("pending_action") and state["pending_action"].get("action") == "await_return_image":
        if state.get("image"):
            state["intent"] = "return_image"
            return state

    if state.get("pending_action") and state["pending_action"].get("action") == "confirm_return":
        if _is_yes(raw_q):
            state["intent"] = "return_confirm"
            return state
        if _is_no(raw_q):
            state["intent"] = "return_cancel"
            return state

        tracking = state["pending_action"].get("tracking_number")
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts={
                "return": {
                    "tracking_number": tracking,
                    "next_step": "awaiting_confirmation_yes_no",
                }
            },
        )
        state["confidence_score"] = 1.0
        state["intent"] = None
        return state

    # reset state
    state["shopcore_ctx"] = None
    state["shipstream_ctx"] = None
    state["payguard_ctx"] = None
    state["caredesk_ctx"] = None
    state["pending_action"] = None
    state["facts"] = None
    state["final_response"] = None

    asks_return_status = any(
        k in q for k in ["return created", "return status", "is there a return"]
    )
    has_any_tracking_id = bool(re.search(r"\b(?:fwd|rev|ndr|exc)-\d+\b", raw_q, re.I))

    is_complex_query = (
        ("ticket" in q or "support" in q or "case" in q)
        and any(k in q for k in ["ordered", "order", "bought", "purchase"])
        and any(k in q for k in ["hasn't arrived", "hasnt arrived", "not arrived", "not delivered", "late"])
        and not has_any_tracking_id
    )

    has_product_hint = bool(
        re.search(r"\"[^\"]+\"|'[^']+'", raw_q)
        or re.search(r"\bga?mm?ing\s+monitor\b", raw_q, re.I)
    )
    asks_paid_amount = bool(
        has_product_hint
        and (
            "paid" in q
            or "price" in q
            or "how much" in q
            or "amount" in q
            or "cost" in q
        )
    )

    order_id_match = re.search(r"\border\s*(\d{3,})\b", raw_q, re.I)
    asks_paid_amount_for_order = bool(
        order_id_match
        and (
            "paid" in q
            or "price" in q
            or "how much" in q
            or "amount" in q
            or "cost" in q
        )
    )

    if asks_paid_amount_for_order:
        state["intent"] = "paid_amount_order"
        return state

    if asks_paid_amount:
        state["intent"] = "paid_amount"
        return state

    if is_complex_query:
        state["intent"] = "complex_query"
        return state

    if asks_return_status and has_any_tracking_id:
        state["intent"] = "return_status"
        return state

    wants_return = any(k in q for k in ["return", "send back", "refund"])

    if wants_return and has_any_tracking_id:
        state["intent"] = "return_request"
        return state

    has_user_identity = bool(state.get("user_email"))
    has_tracking_id = has_any_tracking_id

    if has_tracking_id and not has_user_identity:
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts={"system": {"require_identity": True}},
        )
        state["confidence_score"] = 1.0
        return state

    if has_tracking_id:
        state["intent"] = "shipstream"
    elif any(k in q for k in ["wallet", "balance", "payment", "refund"]):
        state["intent"] = "payguard"
    elif any(k in q for k in ["track", "shipment", "delivery"]):
        state["intent"] = "shipstream"
    else:
        state["intent"] = "shopcore"

    return state


def _extract_product_name(raw_query: str) -> Optional[str]:
    text = raw_query or ""

    m = re.search(r"\"([^\"]+)\"", text)
    if m:
        return (m.group(1) or "").strip() or None

    m = re.search(r"'([^']+)'", text)
    if m:
        return (m.group(1) or "").strip() or None

    if re.search(r"\bga?mm?ing\s+monitor\b", text, re.I):
        return "Gaming Monitor"

    return None


async def handle_complex_query(state: SupervisorState) -> SupervisorState:
    raw_query = state.get("query") or ""
    state["decision_trace"].append({"agent": "Supervisor", "reason": "Complex query orchestration"})

    product_name = _extract_product_name(raw_query)
    if not product_name:
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"shopcore": {"need_product_name": True}},
        )
        state["confidence_score"] = 1.0
        return state

    shop = await lookup_order_for_user_product.ainvoke({
        "user_email": state.get("user_email") or "",
        "product_name": product_name,
    })

    if not isinstance(shop, dict) or not shop.get("found"):
        facts = {"shopcore": shop if isinstance(shop, dict) else {"found": False}}
        state["facts"] = facts
        state["final_response"] = _synthesize_answer(user_message=raw_query, facts=facts)
        state["confidence_score"] = 0.7
        return state

    order_id = shop.get("order_id")
    user_id = shop.get("user_id")

    ship = None
    if isinstance(order_id, int):
        ship = await tracking_for_order.ainvoke({"order_id": order_id})

    care = None
    if isinstance(user_id, int):
        care = await latest_ticket_status.ainvoke({"user_id": user_id, "order_id": order_id})

    facts: Dict[str, Any] = {
        "shopcore": shop,
        "shipstream": ship if isinstance(ship, dict) else {"found": False, "reason": "shipstream_unavailable"},
        "caredesk": care if isinstance(care, dict) else {"found": False, "reason": "caredesk_unavailable"},
    }
    state["facts"] = facts
    state["final_response"] = _synthesize_answer(user_message=raw_query, facts=facts)
    state["confidence_score"] = 1.0
    return state


async def handle_paid_amount(state: SupervisorState) -> SupervisorState:
    raw_query = state.get("query") or ""
    state["decision_trace"].append({"agent": "Supervisor", "reason": "Payment amount lookup"})

    product_name = _extract_product_name(raw_query)
    if not product_name:
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"shopcore": {"need_product_name": True}},
        )
        state["confidence_score"] = 1.0
        return state

    shop = await lookup_order_for_user_product.ainvoke({
        "user_email": state.get("user_email") or "",
        "product_name": product_name,
    })

    if not isinstance(shop, dict) or not shop.get("found"):
        facts = {"shopcore": shop if isinstance(shop, dict) else {"found": False}}
        state["facts"] = facts
        state["final_response"] = _synthesize_answer(user_message=raw_query, facts=facts)
        state["confidence_score"] = 0.7
        return state

    order_id = shop.get("order_id")
    product_id = shop.get("product_id")

    amount = None
    source = None

    if isinstance(order_id, int):
        txn = await sync_to_async(
            lambda: Transaction.objects.using("payguard")
            .filter(order_id=order_id, type__iexact="Debit")
            .order_by("-timestamp")
            .first()
        )()
        if txn and getattr(txn, "amount", None) is not None:
            amount = str(txn.amount)
            source = "transaction"

    if amount is None and isinstance(product_id, int):
        prod = await sync_to_async(
            lambda: Product.objects.using("shopcore").filter(id=product_id).first()
        )()
        if prod and getattr(prod, "price", None) is not None:
            amount = str(prod.price)
            source = "product_price"

    facts: Dict[str, Any] = {
        "shopcore": shop,
        "payguard": {
            "order_id": order_id,
            "amount": amount,
            "source": source,
            "found": bool(amount),
        },
    }
    state["facts"] = facts

    display_product = shop.get("product_name") or product_name

    if amount:
        state["final_response"] = (
            f"You paid {amount} for '{display_product}' (order {order_id})."
        )
        state["confidence_score"] = 1.0
        return state

    state["final_response"] = (
        f"I found your order {order_id} for '{display_product}', but I don't have the payment amount recorded."
    )
    state["confidence_score"] = 0.7
    return state


async def handle_paid_amount_for_order(state: SupervisorState) -> SupervisorState:
    raw_query = state.get("query") or ""
    state["decision_trace"].append({"agent": "Supervisor", "reason": "Payment amount lookup (order)"})

    m = re.search(r"\border\s*(\d{3,})\b", raw_query, re.I)
    if not m:
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"payguard": {"need_order_id": True}},
        )
        state["confidence_score"] = 1.0
        return state

    try:
        order_id = int(m.group(1))
    except Exception:
        order_id = None

    if not order_id:
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"payguard": {"need_order_id": True}},
        )
        state["confidence_score"] = 1.0
        return state

    txn = await sync_to_async(
        lambda: Transaction.objects.using("payguard")
        .filter(order_id=order_id, type__iexact="Debit")
        .order_by("-timestamp")
        .first()
    )()

    amount = str(txn.amount) if txn and getattr(txn, "amount", None) is not None else None

    order = await sync_to_async(
        lambda: Order.objects.using("shopcore").select_related("product").filter(id=order_id).first()
    )()
    product_name = None
    if order and getattr(order, "product", None):
        product_name = getattr(order.product, "name", None)

    facts: Dict[str, Any] = {
        "shopcore": {
            "order_id": order_id,
            "product_name": product_name,
            "found": bool(order),
        },
        "payguard": {
            "order_id": order_id,
            "amount": amount,
            "found": bool(amount),
        },
    }
    state["facts"] = facts

    if amount:
        if product_name:
            state["final_response"] = f"You paid {amount} for '{product_name}' (order {order_id})."
        else:
            state["final_response"] = f"You paid {amount} for order {order_id}."
        state["confidence_score"] = 1.0
        return state

    if order:
        state["final_response"] = (
            f"I found order {order_id}, but I don't have the payment amount recorded."
        )
        state["confidence_score"] = 0.7
        return state

    state["final_response"] = f"I couldn't find order {order_id}."
    state["confidence_score"] = 1.0
    return state

async def handle_return_status(state: SupervisorState) -> SupervisorState:
    raw_query = state.get("query") or ""

    match = re.search(r"\b(FWD-\d+)\b", raw_query, re.I)
    if not match:
        state["final_response"] = "Please provide a valid shipment ID."
        state["confidence_score"] = 1.0
        return state

    tracking = match.group(1).upper()

    # --------------------------------------------------
    # Delegate return-status lookup to ShipStream agent
    # --------------------------------------------------
    result = await check_return_status.ainvoke({
        "tracking_number": tracking,
    })

    if not isinstance(result, dict):
        state["final_response"] = (
            "I couldn’t retrieve the return information right now."
        )
        state["confidence_score"] = 0.5
        return state

    # --------------------------------------------------
    # Optional ownership verification (ShopCore authority)
    # --------------------------------------------------
    order_id = result.get("order_id")
    if order_id:
        order = await sync_to_async(
            lambda: Order.objects
            .using("shopcore")
            .select_related("user")
            .filter(id=order_id)
            .first()
        )()

        if order and getattr(order, "user", None):
            owner_email = (getattr(order.user, "email", "") or "").strip().lower()
            requester_email = (state.get("user_email") or "").strip().lower()

            if owner_email and requester_email and owner_email != requester_email:
                state["final_response"] = (
                    "I’m unable to share return details for this shipment "
                    "because it does not belong to your account."
                )
                state["confidence_score"] = 1.0
                return state

    # --------------------------------------------------
    # Success: relay agent-authored message
    # --------------------------------------------------
    state["final_response"] = result.get("message")
    state["confidence_score"] = 1.0
    return state


async def handle_return_image(state: SupervisorState) -> SupervisorState:
    pending = state.get("pending_action") or {}
    tracking = (pending.get("tracking_number") or "").strip().upper() or None
    image = state.get("image")

    if not tracking:
        state["pending_action"] = None
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts={"return": {"error": "missing_tracking_for_image"}},
        )
        state["confidence_score"] = 0.5
        return state

    if not image:
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts={
                "return": {
                    "tracking_number": tracking,
                    "stage": "awaiting_image",
                    "requirement": "item_condition_image",
                }
            },
        )
        state["confidence_score"] = 1.0
        return state

    result = await submit_return_image.ainvoke({
        "tracking_number": tracking,
        "user_email": state.get("user_email"),
        "image": image,
    })

    return_id = None
    if isinstance(result, dict):
        return_id = (result.get("return_id") or "").strip() or None

    state["pending_action"] = None
    state["facts"] = {
        "return": {
            "tracking_number": tracking,
            "return_id": return_id,
            "stage": "processed",
        }
    }

    if return_id:
        state["final_response"] = (
            f"Your return has been processed successfully. Return ID: {return_id}. "
            "Do you need help with anything else?"
        )
        state["confidence_score"] = 1.0
        return state

    state["final_response"] = _synthesize_answer(
        user_message=state.get("query") or "",
        facts=state["facts"],
    )
    state["confidence_score"] = 0.7
    return state


async def handle_return_request(state: SupervisorState) -> SupervisorState:
    raw_query = state.get("query") or ""
    match = re.search(r"\b(FWD-\d+)\b", raw_query, re.I)
    if not match:
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"return": {"need_tracking_number": True}},
        )
        state["confidence_score"] = 1.0
        return state

    tracking = match.group(1).upper()

    result = await check_return_eligibility.ainvoke({
        "tracking_number": tracking,
    })

    if not isinstance(result, dict):
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"return": {"tracking_number": tracking, "eligibility_check": "failed"}},
        )
        state["confidence_score"] = 0.5
        return state

    if not result.get("eligible"):
        state["final_response"] = result.get("message")
        state["confidence_score"] = 1.0
        return state

    state["pending_action"] = {
        "action": "confirm_return",
        "tracking_number": tracking,
    }

    state["facts"] = {
        "return": {
            "tracking_number": tracking,
            "eligible": True,
            "next_step": "awaiting_confirmation_yes_no",
        }
    }
    state["final_response"] = result.get("message")
    state["confidence_score"] = 1.0
    return state


async def handle_return_confirm(state: SupervisorState) -> SupervisorState:
    pending = state.get("pending_action") or {}
    tracking = pending.get("tracking_number")

    # -----------------------------
    # Missing tracking number
    # -----------------------------
    if not tracking:
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts={"return": {"error": "missing_tracking_for_confirmation"}},
        )
        state["confidence_score"] = 0.5
        return state

    # -----------------------------
    # Ask ShipStream to initiate return
    # -----------------------------
    result = await initiate_return.ainvoke({
        "tracking_number": tracking,
    })

    if not isinstance(result, dict):
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts={
                "return": {
                    "tracking_number": tracking,
                    "initiate": "failed",
                }
            },
        )
        state["confidence_score"] = 0.5
        return state

    # -----------------------------
    # SUCCESS → Await image upload
    # -----------------------------
    state["facts"] = {
        "return": {
            "tracking_number": tracking,
            "stage": "awaiting_image",
            "requirement": "item_condition_image",
        }
    }

    state["pending_action"] = {
        "action": "await_return_image",
        "tracking_number": tracking,
    }

    state["final_response"] = _synthesize_answer(
        user_message=state.get("query") or "",
        facts=state["facts"],
    )

    state["confidence_score"] = 1.0
    return state

async def handle_return_cancel(state: SupervisorState) -> SupervisorState:
    pending = state.get("pending_action") or {}
    tracking = pending.get("tracking_number")
    state["pending_action"] = None
    state["final_response"] = _synthesize_answer(
        user_message=state.get("query") or "",
        facts={"return": {"tracking_number": tracking, "cancelled": True}},
    )
    state["confidence_score"] = 1.0
    return state


def route_after_intent(state: SupervisorState) -> str:
    intent = state.get("intent")
    if intent:
        return intent
    if state.get("final_response"):
        return "aggregate"
    return "shopcore"

# -------------------------------------------------------------------
# Initialize agents (singletons)
# -------------------------------------------------------------------

SHOPCORE_AGENT = build_shopcore_agent()
SHIPSTREAM_AGENT = build_shipstream_agent()
PAYGUARD_AGENT = build_payguard_agent()
CAREDESK_AGENT = build_caredesk_agent()

# -------------------------------------------------------------------
# Agent Calls
# -------------------------------------------------------------------

async def call_shopcore(state: SupervisorState) -> SupervisorState:
    state["decision_trace"].append({"agent": "ShopCore", "reason": "User/order resolution"})
    try:
        result = await SHOPCORE_AGENT.ainvoke({
            "input": state["query"],
            "user_email": state["user_email"],
            "product_name": state["query"],
        })
        state["shopcore_ctx"] = result if isinstance(result, dict) else None
    except Exception as e:
        logger.error(f"ShopCore failed: {e}")
        state["shopcore_ctx"] = None
    return state


async def call_shipstream(state: SupervisorState) -> SupervisorState:
    state["decision_trace"].append({
        "agent": "ShipStream",
        "reason": "Shipment lifecycle lookup"
    })

    raw_query = state.get("query") or ""

    # Normalize unicode dashes → ASCII
    normalized_query = re.sub(r"[‐-‒–—−]", "-", raw_query)

    match = re.search(r"\b(FWD|REV|NDR|EXC)-\d+\b", normalized_query, re.I)
    tracking = match.group(0).upper() if match else None

    # --------------------------------------------------
    # No tracking ID provided
    # --------------------------------------------------
    if not tracking:
        state["final_response"] = _synthesize_answer(
            user_message=raw_query,
            facts={"shipstream": {"need_tracking_number": True}},
        )
        state["confidence_score"] = 1.0
        return state

    # ==================================================
    # FORWARD SHIPMENT (FWD)
    # ==================================================
    if tracking.startswith("FWD-"):
        shipment = await sync_to_async(
            lambda: Shipment.objects
            .using("shipstream")
            .filter(tracking_number__iexact=tracking)
            .first()
        )()

        if not shipment:
            state["final_response"] = _synthesize_answer(
                user_message=raw_query,
                facts={"shipstream": {"tracking_number": tracking, "found": False}},
            )
            state["confidence_score"] = 1.0
            return state

        # Explicit ETA handling (NO hallucination)
        eta = (
            str(shipment.estimated_arrival)
            if shipment.status == "Delivered" and shipment.estimated_arrival
            else "Not available"
        )

        state["shipstream_ctx"] = {
            "type": "forward",
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "customer": shipment.customer_name,
            "amount": str(shipment.amount),
            "estimated_arrival": eta,
        }
        return state

    # ==================================================
    # REVERSE SHIPMENT (REV)
    # ==================================================
    if tracking.startswith("REV-"):
        reverse = await sync_to_async(
            lambda: ReverseShipment.objects
            .using("shipstream")
            .filter(reverse_number=tracking)
            .first()
        )()

        if not reverse:
            state["final_response"] = _synthesize_answer(
                user_message=raw_query,
                facts={"shipstream": {"tracking_number": tracking, "found": False}},
            )
            state["confidence_score"] = 1.0
            return state

        state["shipstream_ctx"] = {
            "type": "reverse",
            "reverse_number": tracking,
            "original_awb": reverse.original_shipment_id,
            "return_date": str(reverse.return_date),
            "reason": reverse.reason,
            "refund_status": reverse.refund_status,
        }
        return state

    # ==================================================
    # NDR EVENT
    # ==================================================
    if tracking.startswith("NDR-"):
        ndr = await sync_to_async(
            lambda: NdrEvent.objects
            .using("shipstream")
            .filter(ndr_number=tracking)
            .first()
        )()

        if not ndr:
            state["final_response"] = _synthesize_answer(
                user_message=raw_query,
                facts={"shipstream": {"tracking_number": tracking, "found": False}},
            )
            state["confidence_score"] = 1.0
            return state

        state["shipstream_ctx"] = {
            "type": "ndr",
            "ndr_number": tracking,
            "original_awb": ndr.original_shipment_id,
            "ndr_date": str(ndr.ndr_date),
            "issue": ndr.issue,
            "attempts": ndr.attempts,
            "final_outcome": ndr.final_outcome,
        }
        return state

    # ==================================================
    # EXCHANGE SHIPMENT
    # ==================================================
    if tracking.startswith("EXC-"):
        exc = await sync_to_async(
            lambda: ExchangeShipment.objects
            .using("shipstream")
            .filter(exchange_number=tracking)
            .first()
        )()

        if not exc:
            state["final_response"] = _synthesize_answer(
                user_message=raw_query,
                facts={"shipstream": {"tracking_number": tracking, "found": False}},
            )
            state["confidence_score"] = 1.0
            return state

        state["shipstream_ctx"] = {
            "type": "exchange",
            "exchange_number": tracking,
            "original_awb": exc.original_shipment_id,
            "exchange_date": str(exc.exchange_date),
            "new_item": exc.new_item,
            "status": exc.status,
        }
        return state

    # --------------------------------------------------
    # Fallback (should never hit)
    # --------------------------------------------------
    state["final_response"] = _synthesize_answer(
        user_message=raw_query,
        facts={"shipstream": {"tracking_number": tracking, "unsupported_type": True}},
    )
    state["confidence_score"] = 0.5
    return state




async def call_payguard(state: SupervisorState) -> SupervisorState:
    logger.warning("PAYGUARD AGENT CALLED")

    state["decision_trace"].append({"agent": "PayGuard", "reason": "Wallet lookup"})
    try:
        result = await PAYGUARD_AGENT.ainvoke({
            "input": state["query"],
            "user_email": state["user_email"],
        })
        state["payguard_ctx"] = result if isinstance(result, dict) else None
    except Exception as e:
        logger.error(f"PayGuard failed: {e}")
        state["payguard_ctx"] = None
    return state


async def call_caredesk(state: SupervisorState) -> SupervisorState:
    state["decision_trace"].append({"agent": "CareDesk", "reason": "Support inquiry"})
    try:
        result = await CAREDESK_AGENT.ainvoke({
            "input": state["query"],
            "user_email": state["user_email"],
        })
        state["caredesk_ctx"] = result if isinstance(result, dict) else None
    except Exception as e:
        logger.error(f"CareDesk failed: {e}")
        state["caredesk_ctx"] = None
    return state

# -------------------------------------------------------------------
# Aggregate Response
# -------------------------------------------------------------------

def aggregate_response(state: SupervisorState) -> SupervisorState:
    if state.get("final_response"):
        return state

    facts = state.get("facts") or {}

    if facts.get("constraint") == "wallet_not_scoped_to_shipment":
        prompt = get_response_synthesizer_prompt()
        msg = (
            "SYSTEM_FACT:\n"
            "Wallet balances are account-level data and cannot be scoped "
            "to shipment or tracking IDs.\n\n"
            "USER_QUERY:\n"
            f"{state['query']}"
        )

        out = RESPONSE_SYNTH_LLM.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=msg),
        ])

        state["final_response"] = out.content.strip()
        state["confidence_score"] = 1.0
        return state

    if state.get("shipstream_ctx"):
        s = state["shipstream_ctx"]
        facts = {"shipstream": s}
        state["facts"] = facts
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts=facts,
        )
        state["confidence_score"] = 1.0
        return state

    if state.get("payguard_ctx"):
        facts = {"payguard": state["payguard_ctx"]}
        state["facts"] = facts
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts=facts,
        )
        state["confidence_score"] = 1.0
        return state

    if state.get("caredesk_ctx"):
        facts = {"caredesk": state["caredesk_ctx"]}
        state["facts"] = facts
        state["final_response"] = _synthesize_answer(
            user_message=state.get("query") or "",
            facts=facts,
        )
        state["confidence_score"] = 1.0
        return state

    state["final_response"] = _synthesize_answer(
        user_message=state.get("query") or "",
        facts={"system": {"no_matching_record": True}},
    )
    state["confidence_score"] = 0.3
    return state


# -------------------------------------------------------------------
# Build Graph
# -------------------------------------------------------------------

def build_supervisor_graph():
    graph = StateGraph(SupervisorState)

    # -----------------------------
    # Core routing
    # -----------------------------
    graph.add_node("intent", intent_gate)

    # -----------------------------
    # Return flow (explicit lifecycle)
    # -----------------------------
    graph.add_node("return_request", handle_return_request)
    graph.add_node("return_confirm", handle_return_confirm)
    graph.add_node("return_image", handle_return_image)
    graph.add_node("return_cancel", handle_return_cancel)
    graph.add_node("return_status", handle_return_status)

    # -----------------------------
    # Complex cross-domain query
    # -----------------------------
    graph.add_node("complex_query", handle_complex_query)

    # -----------------------------
    # Cross-domain: paid amount
    # -----------------------------
    graph.add_node("paid_amount", handle_paid_amount)
    graph.add_node("paid_amount_order", handle_paid_amount_for_order)

    # -----------------------------
    # Domain agents
    # -----------------------------
    graph.add_node("shopcore", call_shopcore)
    graph.add_node("shipstream", call_shipstream)
    graph.add_node("payguard", call_payguard)
    graph.add_node("caredesk", call_caredesk)

    # -----------------------------
    # Final synthesis
    # -----------------------------
    graph.add_node("aggregate", aggregate_response)

    graph.set_entry_point("intent")

    # -----------------------------
    # Intent-based routing
    # -----------------------------
    graph.add_conditional_edges(
        "intent",
        route_after_intent,
        {
            # Return lifecycle
            "return_request": "return_request",
            "return_confirm": "return_confirm",
            "return_image": "return_image",
            "return_cancel": "return_cancel",
            "return_status": "return_status",

            # Complex orchestration
            "complex_query": "complex_query",

            # Paid amount
            "paid_amount": "paid_amount",
            "paid_amount_order": "paid_amount_order",

            # Direct fallback when intent_gate already produced final_response
            "aggregate": "aggregate",

            # Default domain routing
            "shopcore": "shopcore",
            "shipstream": "shipstream",
            "payguard": "payguard",
            "caredesk": "caredesk",
        },
    )

    # -----------------------------
    # All paths converge to aggregate
    # -----------------------------
    graph.add_edge("return_request", "aggregate")
    graph.add_edge("return_confirm", "aggregate")
    graph.add_edge("return_image", "aggregate")
    graph.add_edge("return_cancel", "aggregate")
    graph.add_edge("return_status", "aggregate")

    graph.add_edge("complex_query", "aggregate")
    graph.add_edge("paid_amount", "aggregate")
    graph.add_edge("paid_amount_order", "aggregate")

    graph.add_edge("shopcore", "aggregate")
    graph.add_edge("shipstream", "aggregate")
    graph.add_edge("payguard", "aggregate")
    graph.add_edge("caredesk", "aggregate")

    graph.add_edge("aggregate", END)

    return graph.compile()


SUPERVISOR_GRAPH = build_supervisor_graph()


async def handle_refund_after_return(state: SupervisorState) -> SupervisorState:
    tracking = state["pending_action"]["tracking_number"]

    # 1️⃣ Ask ShipStream for order_id
    ship_result = await SHIPSTREAM_AGENT.ainvoke({
        "action": "get_order_for_tracking",
        "tracking_number": tracking,
    })

    order_id = ship_result.get("order_id")
    user_id = ship_result.get("user_id")

    # 2️⃣ Trigger refund
    refund = await PAYGUARD_AGENT.ainvoke({
        "order_id": order_id
    })

    # 3️⃣ Auto-create CareDesk ticket
    await CAREDESK_AGENT.ainvoke({
        "user_id": user_id,
        "order_id": order_id,
        "tracking_number": tracking,
        "refund_status": refund.get("message"),
    })

    state["final_response"] = (
        f"Your return has been confirmed.\n\n"
        f"{refund.get('message')}\n\n"
        "A support ticket has also been created to track your refund."
    )

    state["confidence_score"] = 1.0
    state.pop("pending_action", None)

    return state

# -------------------------------------------------------------------
# Public Runner
# -------------------------------------------------------------------

async def run_supervisor(
    query: str,
    user_email: str,
    user_name: Optional[str] = None,
    pending_action: Optional[Dict[str, Any]] = None,
    image: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> dict:
    initial_state: SupervisorState = {
        "query": query,
        "user_email": user_email,
        "user_name": user_name,
        "image": image,
        "reference_id": reference_id,
        "intent": None,
        "pending_action": pending_action,

        "shopcore_ctx": None,
        "shipstream_ctx": None,
        "payguard_ctx": None,
        "caredesk_ctx": None,

        "facts": None,
        "decision_trace": [],
        "confidence_score": 0.0,
        "final_response": None,
    }

    result = await SUPERVISOR_GRAPH.ainvoke(initial_state)

    pending = result.get("pending_action")
    needs_image = bool(isinstance(pending, dict) and pending.get("action") == "await_return_image")
    ref = None
    if needs_image and isinstance(pending, dict):
        ref = pending.get("tracking_number")

    return {
        "answer": result["final_response"],
        "confidence": result["confidence_score"],
        "decision_trace": result["decision_trace"],
        "facts": result.get("facts") or {},
        "pending_action": pending,
        "needs_image": needs_image,
        "reference_id": ref,
    }
