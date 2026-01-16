from typing import TypedDict, Optional, Dict, Any, List
from dataclasses import dataclass
import os
import re
import json

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# -------------------------------------------------------------------
# Django setup (required for ORM access inside agents)
# -------------------------------------------------------------------

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django
django.setup()

# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

import asyncio
from langchain_core.runnables import Runnable
from omniflow.utils.logging import get_logger
from omniflow.utils.config import settings

from django.db import connections

# Agent builders
from omniflow.agents.langchain_based_agents.shopcore_agent import build_shopcore_agent
from omniflow.agents.langchain_based_agents.shipstream_agent import build_shipstream_agent
from omniflow.agents.langchain_based_agents.payguard_agent import build_payguard_agent
from omniflow.agents.langchain_based_agents.caredesk_agent import build_caredesk_agent

from omniflow.shipstream.models import Shipment, ReverseShipment, NdrEvent, ExchangeShipment
from omniflow.utils.prompts import get_response_synthesizer_prompt
from omniflow.utils.config import settings as pydantic_settings

logger = get_logger(__name__)

RESPONSE_SYNTH_LLM = ChatOpenAI(
    temperature=0,
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    api_key=pydantic_settings.OPENAI_API_KEY,
    timeout=15,
    max_retries=1,
)


def _contains_only_allowed_ids(text: str, allowed_ids: set[str]) -> bool:
    found = set(re.findall(r"\b(?:FWD|REV|NDR|EXC)-\d+\b", text or "", flags=re.IGNORECASE))
    found_norm = {x.upper() for x in found}
    return found_norm.issubset({x.upper() for x in allowed_ids})


def _contains_banned_filler(text: str) -> bool:
    t = (text or "").lower()
    banned = [
        "get back to you",
        "let me check",
        "i'll check",
        "one moment",
        "give me a moment",
        "checking",
    ]
    return any(b in t for b in banned)


def _fallback_grounded_sentence(user_query: str, facts: dict) -> str:
    # Keep this natural but deterministic and grounded (no filler).
    ship = (facts or {}).get("shipstream") or {}
    raw = ship.get("raw_response") or {}
    tn = raw.get("tracking_number") or raw.get("reverse_number") or raw.get("ndr_number") or raw.get("exchange_number")
    status = raw.get("current_status") or raw.get("status")
    eta = raw.get("estimated_arrival")
    if tn and (status or eta):
        if status and eta:
            return f"{tn} is currently {status}. Estimated arrival is {eta}."
        if status:
            return f"{tn} is currently {status}."
        return f"Estimated arrival for {tn} is {eta}."
    return "I don’t have enough verified data to answer that yet. Could you share the tracking ID (e.g., FWD-1013)?"


def _synthesize_natural_answer(user_query: str, facts: dict, allowed_ids: set[str]) -> str | None:
    try:
        prompt = get_response_synthesizer_prompt()
        msg = (
            "USER_MESSAGE:\n"
            f"{user_query}\n\n"
            "FACTS_JSON:\n"
            f"{json.dumps(facts, ensure_ascii=False)}"
        )
        def _invoke(system_prompt: str) -> str:
            out = RESPONSE_SYNTH_LLM.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=msg),
            ])
            return (getattr(out, "content", "") or "").strip()

        text = _invoke(prompt)
        if not text:
            return None

        # Basic grounding validation: don't allow new tracking/return IDs to appear.
        if not _contains_only_allowed_ids(text, allowed_ids):
            return None

        # Hard ban filler phrases; retry once with stricter instruction.
        if _contains_banned_filler(text):
            stricter = prompt + "\n\nHard constraint: NEVER say phrases like 'get back to you' or 'let me check'. Answer directly with the facts now."
            text2 = _invoke(stricter)
            if text2 and _contains_only_allowed_ids(text2, allowed_ids) and not _contains_banned_filler(text2):
                return text2
            return _fallback_grounded_sentence(user_query, facts)

        return text
    except Exception:
        return None

# -------------------------------------------------------------------
# Supervisor State
# -------------------------------------------------------------------

# supervisor_graph.py

class SupervisorState(TypedDict):
    query: str
    user_email: str

    shopcore_ctx: Optional[Dict[str, Any]]
    shipstream_ctx: Optional[Dict[str, Any]]
    payguard_ctx: Optional[Dict[str, Any]]
    caredesk_ctx: Optional[Dict[str, Any]]

    decision_trace: list
    confidence_score: float

    final_response: Optional[str]


def _is_smalltalk(query: str) -> bool:
    return False


def intent_gate(state: SupervisorState) -> SupervisorState:
    return state


def _route_after_intent(state: SupervisorState) -> str:
    return "shopcore"



# -------------------------------------------------------------------
# Evaluation (Hallucination / Grounding)
# -------------------------------------------------------------------

@dataclass
class EvaluationResult:
    grounded: bool
    hallucination_risk: float
    agent_outputs_used: int


def evaluate_response(agent_outputs: List[str]) -> EvaluationResult:
    """
    Deterministic grounding evaluation.
    No LLM usage.
    """
    if not agent_outputs:
        return EvaluationResult(
            grounded=False,
            hallucination_risk=1.0,
            agent_outputs_used=0
        )

    return EvaluationResult(
        grounded=True,
        hallucination_risk=0.0,
        agent_outputs_used=len(agent_outputs)
    )


# -------------------------------------------------------------------
# Initialize Agents (singletons)
# -------------------------------------------------------------------

logger.info("Initializing LangChain agents...")

SHOPCORE_AGENT = build_shopcore_agent()
SHIPSTREAM_AGENT = build_shipstream_agent()
PAYGUARD_AGENT = build_payguard_agent()
CAREDESK_AGENT = build_caredesk_agent()

logger.info("All agents initialized successfully")

# -------------------------------------------------------------------
# Graph Nodes
# -------------------------------------------------------------------

async def call_shopcore(state: SupervisorState) -> SupervisorState:
    state["decision_trace"].append({
        "agent": "ShopCore",
        "reason": "Initial order & user identification required"
    })
    logger.info("Calling ShopCore agent")

    try:
        result = await SHOPCORE_AGENT.ainvoke({
            "input": state["query"],
            "user_email": state["user_email"],
            "product_name": state["query"],
        })

        if isinstance(result, dict):
            state["shopcore_ctx"] = {
                "order_id": result.get("order_id"),
                "user_id": result.get("user_id"),
                "order_status": result.get("order_status"),
                "raw_response": result,
            }
        else:
            state["shopcore_ctx"] = None

        logger.info("ShopCore agent executed successfully")

    except Exception as e:
        logger.error(f"ShopCore agent failed: {e}")
        state["shopcore_ctx"] = None

    return state


async def call_shipstream(state: SupervisorState) -> SupervisorState:
    # If ShopCore didn't resolve an order_id, try extracting a tracking number
    # directly from the user query (e.g. FWD-1013, REV-9001, NDR-504, EXC-201).
    order_id = (state.get("shopcore_ctx") or {}).get("order_id")
    tracking_match = re.search(r"\b(FWD|REV|NDR|EXC)-\d+\b", state.get("query", ""), re.IGNORECASE)
    tracking_number = tracking_match.group(0).upper() if tracking_match else None

    if not order_id and not tracking_number:
        state["decision_trace"].append({
            "agent": "ShipStream",
            "reason": "Skipped – no order_id or tracking number available"
        })
        return state

    state["decision_trace"].append({
        "agent": "ShipStream",
        "reason": "Shipment/return tracking requested"
    })

    # Deterministic ORM lookup first (avoids hallucinations and ensures we use SQLite data)
    if tracking_number:
        try:
            try:
                shipstream_db_name = connections["shipstream"].settings_dict.get("NAME")
            except Exception:
                shipstream_db_name = None

            prefix = tracking_number.split("-", 1)[0].upper()

            # REV/NDR/EXC are their own primary identifiers and shouldn't be looked up via Shipment.
            if prefix == "REV":
                rev = ReverseShipment.objects.using("shipstream").filter(reverse_number=tracking_number).first()
                if rev:
                    state["shipstream_ctx"] = {
                        "return_created": True,
                        "reverse_number": rev.reverse_number,
                        "refund_status": rev.refund_status,
                        "raw_response": {
                            "reverse_number": rev.reverse_number,
                            "refund_status": rev.refund_status,
                            "reason": rev.reason,
                            "return_date": str(rev.return_date) if rev.return_date else None,
                            "original_shipment": rev.original_shipment_id,
                        },
                    }
                    logger.info("ShipStream ORM lookup succeeded (ReverseShipment)")
                    return state

            if prefix == "NDR":
                ndr = NdrEvent.objects.using("shipstream").filter(ndr_number=tracking_number).first()
                if ndr:
                    state["shipstream_ctx"] = {
                        "raw_response": {
                            "ndr_number": ndr.ndr_number,
                            "issue": ndr.issue,
                            "attempts": ndr.attempts,
                            "final_outcome": ndr.final_outcome,
                            "ndr_date": str(ndr.ndr_date) if ndr.ndr_date else None,
                            "original_shipment": ndr.original_shipment_id,
                        },
                    }
                    logger.info("ShipStream ORM lookup succeeded (NdrEvent)")
                    return state

            if prefix == "EXC":
                exc = ExchangeShipment.objects.using("shipstream").filter(exchange_number=tracking_number).first()
                if exc:
                    state["shipstream_ctx"] = {
                        "raw_response": {
                            "exchange_number": exc.exchange_number,
                            "status": exc.status,
                            "new_item": exc.new_item,
                            "exchange_date": str(exc.exchange_date) if exc.exchange_date else None,
                            "original_shipment": exc.original_shipment_id,
                        },
                    }
                    logger.info("ShipStream ORM lookup succeeded (ExchangeShipment)")
                    return state

            # Default: assume forward shipment id.
            shipment = Shipment.objects.using("shipstream").filter(tracking_number=tracking_number).first()
            if shipment:
                rev = ReverseShipment.objects.using("shipstream").filter(original_shipment_id=shipment.tracking_number).first()
                ndr = NdrEvent.objects.using("shipstream").filter(original_shipment_id=shipment.tracking_number).first()
                exc = ExchangeShipment.objects.using("shipstream").filter(original_shipment_id=shipment.tracking_number).first()

                raw = {
                    "tracking_number": shipment.tracking_number,
                    "estimated_arrival": str(shipment.estimated_arrival) if shipment.estimated_arrival else None,
                    "current_status": shipment.status,
                    "customer": shipment.customer_name,
                    "amount": str(shipment.amount),
                }

                ctx = {
                    "current_status": shipment.status,
                    "raw_response": raw,
                }

                if rev:
                    ctx["return_created"] = True
                    ctx["reverse_number"] = rev.reverse_number
                    ctx["refund_status"] = rev.refund_status
                else:
                    ctx["return_created"] = False

                if ndr:
                    raw.update({
                        "ndr_number": ndr.ndr_number,
                        "ndr_issue": ndr.issue,
                        "ndr_attempts": ndr.attempts,
                        "ndr_outcome": ndr.final_outcome,
                    })

                if exc:
                    raw.update({
                        "exchange_number": exc.exchange_number,
                        "exchange_status": exc.status,
                        "new_item": exc.new_item,
                    })

                state["shipstream_ctx"] = ctx
                logger.info("ShipStream ORM lookup succeeded (Shipment)")
                return state

            # Diagnostics to help debug seeded-ID lookups in long-running servers.
            try:
                counts = {
                    "shipments": Shipment.objects.using("shipstream").count(),
                    "reverse": ReverseShipment.objects.using("shipstream").count(),
                    "ndr": NdrEvent.objects.using("shipstream").count(),
                    "exchange": ExchangeShipment.objects.using("shipstream").count(),
                }
            except Exception:
                counts = None
            logger.info(f"ShipStream lookup miss tracking_number={tracking_number} db={shipstream_db_name} counts={counts}")
        except Exception as e:
            logger.error(f"ShipStream ORM lookup failed: {e}")

    logger.info(f"Calling ShipStream agent for order_id={order_id}, tracking_number={tracking_number}")

    try:
        result = await SHIPSTREAM_AGENT.ainvoke({
            "input": state["query"],
            "order_id": order_id,
            "tracking_number": tracking_number,
        })

        if isinstance(result, dict):
            state["shipstream_ctx"] = {
                "current_status": result.get("current_status") or result.get("shipment_status") or result.get("status"),
                "return_created": result.get("return_created"),
                "reverse_number": result.get("reverse_number"),
                "refund_status": result.get("refund_status"),
                "raw_response": result,
            }
        else:
            state["shipstream_ctx"] = None

        logger.info("ShipStream agent executed successfully")

    except Exception as e:
        logger.error(f"ShipStream agent failed: {e}")
        state["shipstream_ctx"] = None

    return state


async def call_payguard(state: SupervisorState) -> SupervisorState:
    if not state["shopcore_ctx"] or not state["shopcore_ctx"].get("user_id"):
        state["decision_trace"].append({
            "agent": "PayGuard",
            "reason": "Skipped – missing user_id or order_id"
        })
        return state

    state["decision_trace"].append({
        "agent": "PayGuard",
        "reason": "User & order identified → payment check required"
    })
    shopcore = state.get("shopcore_ctx") or {}
    order_id = shopcore.get("order_id")
    user_id = shopcore.get("user_id")

    if not order_id or not user_id:
        logger.info("Skipping PayGuard (missing order_id or user_id)")
        state["payguard_ctx"] = None
        return state

    logger.info(f"Calling PayGuard agent for user_id={user_id}, order_id={order_id}")

    try:
        result = await PAYGUARD_AGENT.ainvoke({
            "input": state["query"],
            "user_id": user_id,
            "order_id": order_id,
        })

        if isinstance(result, dict):
            state["payguard_ctx"] = {
                "balance": result.get("balance"),
                "raw_response": result,
            }
        else:
            state["payguard_ctx"] = None

        logger.info("PayGuard agent executed successfully")

    except Exception as e:
        logger.error(f"PayGuard agent failed: {e}")
        state["payguard_ctx"] = None

    return state


async def call_caredesk(state: SupervisorState) -> SupervisorState:
    if not state["shopcore_ctx"] or not state["shopcore_ctx"].get("user_id"):
        state["decision_trace"].append({
            "agent": "CareDesk",
            "reason": "Skipped – user_id not available"
        })
        return state

    state["decision_trace"].append({
        "agent": "CareDesk",
        "reason": "User identified → ticket status requested"
    })
    user_id = (state.get("shopcore_ctx") or {}).get("user_id")

    if not user_id:
        logger.info("Skipping CareDesk (no user_id)")
        state["caredesk_ctx"] = None
        return state

    logger.info(f"Calling CareDesk agent for user_id={user_id}")

    try:
        result = await CAREDESK_AGENT.ainvoke({
            "input": state["query"],
            "user_id": user_id,
        })

        if isinstance(result, dict):
            state["caredesk_ctx"] = {
                "ticket_status": result.get("status"),
                "raw_response": result,
            }
        else:
            state["caredesk_ctx"] = None

        logger.info("CareDesk agent executed successfully")

    except Exception as e:
        logger.error(f"CareDesk agent failed: {e}")
        state["caredesk_ctx"] = None

    return state


def aggregate_response(state: SupervisorState) -> SupervisorState:
    parts: List[str] = []
    resolved = 0
    expected = 4  # ShopCore, ShipStream, PayGuard, CareDesk

    shopcore = state.get("shopcore_ctx") or {}
    shipstream = state.get("shipstream_ctx") or {}
    payguard = state.get("payguard_ctx") or {}
    caredesk = state.get("caredesk_ctx") or {}

    facts: Dict[str, Any] = {}
    allowed_ids: set[str] = set()

    if shopcore:
        resolved += 1
        order_id = shopcore.get("order_id")
        order_status = shopcore.get("order_status")
        facts["shopcore"] = {}
        if order_id and order_status:
            parts.append(f"I found your order {order_id} — it’s currently {order_status}.")
            facts["shopcore"].update({"order_id": order_id, "order_status": order_status})
            allowed_ids.add(str(order_id))
        elif order_status:
            parts.append(f"I found your order status — it’s currently {order_status}.")
            facts["shopcore"].update({"order_status": order_status})

    if shipstream:
        resolved += 1
        raw = shipstream.get("raw_response") or {}
        tracking_number = raw.get("tracking_number")
        current_status = shipstream.get("current_status")
        facts["shipstream"] = {}
        if tracking_number and current_status:
            parts.append(f"For {tracking_number}, the latest shipment status I can see is {current_status}.")
            facts["shipstream"].update({"tracking_number": tracking_number, "current_status": current_status})
            allowed_ids.add(str(tracking_number))
        elif current_status:
            parts.append(f"The latest shipment status I can see is {current_status}.")
            facts["shipstream"].update({"current_status": current_status})

        return_created = shipstream.get("return_created")
        reverse_number = shipstream.get("reverse_number")
        if return_created is True:
            if reverse_number:
                parts.append(f"A return is already created (return ID {reverse_number}).")
                facts["shipstream"].update({"return_created": True, "return_id": reverse_number})
                allowed_ids.add(str(reverse_number))
            else:
                parts.append("A return is already created.")
                facts["shipstream"].update({"return_created": True})
        elif return_created is False:
            parts.append("I couldn’t find any return created for that shipment.")
            facts["shipstream"].update({"return_created": False})

        refund_status = shipstream.get("refund_status")
        if refund_status:
            parts.append(f"Refund status shows as {refund_status}.")
            facts["shipstream"].update({"refund_status": refund_status})

    if payguard:
        resolved += 1
        balance = payguard.get("balance")
        facts["payguard"] = {}
        if balance:
            parts.append(f"Your wallet balance is {balance}.")
            facts["payguard"].update({"balance": balance})

    if caredesk:
        resolved += 1
        ticket_status = caredesk.get("ticket_status")
        facts["caredesk"] = {}
        if ticket_status:
            parts.append(f"Your latest support ticket status is {ticket_status}.")
            facts["caredesk"].update({"ticket_status": ticket_status})

    # Deterministic ShipStream fallback: if user provided an ID but shipstream_ctx is missing,
    # fetch directly from the isolated shipstream DB and return a direct answer.
    q = (state.get("query") or "")
    q_norm = re.sub(r"[‐‑‒–—−]", "-", q)
    provided_id_match = re.search(r"\b(?:FWD|REV|NDR|EXC)-\d+\b", q_norm, flags=re.IGNORECASE)
    provided_id = provided_id_match.group(0).upper() if provided_id_match else None
    if provided_id and not (state.get("shipstream_ctx") or {}):
        try:
            prefix = provided_id.split("-", 1)[0]
            if prefix == "FWD":
                s = Shipment.objects.using("shipstream").filter(tracking_number=provided_id).first()
                if s:
                    state["shipstream_ctx"] = {
                        "current_status": s.status,
                        "raw_response": {
                            "tracking_number": s.tracking_number,
                            "current_status": s.status,
                            "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
                            "customer": s.customer_name,
                            "amount": str(s.amount),
                        },
                    }

            if prefix == "REV":
                rev = ReverseShipment.objects.using("shipstream").filter(reverse_number=provided_id).first()
                if rev:
                    state["shipstream_ctx"] = {
                        "return_created": True,
                        "reverse_number": rev.reverse_number,
                        "refund_status": rev.refund_status,
                        "raw_response": {
                            "reverse_number": rev.reverse_number,
                            "refund_status": rev.refund_status,
                            "reason": rev.reason,
                            "return_date": str(rev.return_date) if rev.return_date else None,
                            "original_shipment": rev.original_shipment_id,
                        },
                    }

            if prefix == "NDR":
                ndr = NdrEvent.objects.using("shipstream").filter(ndr_number=provided_id).first()
                if ndr:
                    state["shipstream_ctx"] = {
                        "raw_response": {
                            "ndr_number": ndr.ndr_number,
                            "issue": ndr.issue,
                            "attempts": ndr.attempts,
                            "final_outcome": ndr.final_outcome,
                            "ndr_date": str(ndr.ndr_date) if ndr.ndr_date else None,
                            "original_shipment": ndr.original_shipment_id,
                        }
                    }

            if prefix == "EXC":
                exc = ExchangeShipment.objects.using("shipstream").filter(exchange_number=provided_id).first()
                if exc:
                    state["shipstream_ctx"] = {
                        "raw_response": {
                            "exchange_number": exc.exchange_number,
                            "status": exc.status,
                            "new_item": exc.new_item,
                            "exchange_date": str(exc.exchange_date) if exc.exchange_date else None,
                            "original_shipment": exc.original_shipment_id,
                        }
                    }
        except Exception as e:
            logger.error(f"Deterministic ShipStream fallback failed: {e}")

        if not state.get("shipstream_ctx"):
            state["final_response"] = (
                f"I couldn’t find a matching record for {provided_id}. Please double-check the ID and try again."
            )
            return state

    # Keep ShipStream answers LLM-generated but grounded. We only short-circuit with deterministic
    # text when the LLM fails.

    # Confidence = data coverage ratio
    state["confidence_score"] = round(resolved / expected, 2)

    # Let the LLM produce the final paragraph (validated). This also handles greetings/smalltalk
    # when facts are empty.
    synthesized = _synthesize_natural_answer(state.get("query", ""), facts, allowed_ids)
    if synthesized:
        # Final safety net: never allow filler phrases through.
        if _contains_banned_filler(synthesized):
            state["final_response"] = _fallback_grounded_sentence(state.get("query", ""), facts)
        else:
            state["final_response"] = synthesized
        return state

    # Grounded fallback: if we truly have no grounded facts, ask a clarifying question.
    if parts:
        state["final_response"] = " ".join(parts)
        return state

    q = (state.get("query") or "").strip()
    q_lower = q.lower()

    provided_id_match = re.search(r"\b(?:FWD|REV|NDR|EXC)-\d+\b", q, flags=re.IGNORECASE)
    provided_id = provided_id_match.group(0).upper() if provided_id_match else None

    # If the user is asking about a shipment/return/refund but didn't provide an ID.
    if any(k in q_lower for k in ["return", "refund", "rto", "ndr", "exchange", "shipment", "track", "tracking", "delivery"]):
        if provided_id:
            state["final_response"] = (
                f"I couldn’t find a matching record for {provided_id}. "
                "Please double-check the ID (or share an order ID) and try again."
            )
        else:
            state["final_response"] = (
                "I can help — could you share the tracking number (e.g., FWD-1013) "
                "or the order ID so I can look it up?"
            )
        return state

    # If the question looks like an order/account inquiry.
    if any(k in q_lower for k in ["order", "payment", "wallet", "transaction", "charged", "balance"]):
        state["final_response"] = (
            "Sure — can you share your email and either the order ID or the product name you ordered?"
        )
        return state

    # Default fallback
    state["final_response"] = (
        "I couldn’t find a matching record yet. What’s the tracking number or order ID you’re referring to?"
    )

    return state



# -------------------------------------------------------------------
# Build LangGraph
# -------------------------------------------------------------------

def build_supervisor_graph():
    logger.info("Building supervisor LangGraph")

    graph = StateGraph(SupervisorState)

    graph.add_node("intent", intent_gate)

    graph.add_node("shopcore", call_shopcore)
    graph.add_node("shipstream", call_shipstream)
    graph.add_node("payguard", call_payguard)
    graph.add_node("caredesk", call_caredesk)
    graph.add_node("aggregate", aggregate_response)

    graph.set_entry_point("intent")

    graph.add_conditional_edges(
        "intent",
        _route_after_intent,
        {
            "shopcore": "shopcore",
            "aggregate": "aggregate",
        },
    )

    graph.add_edge("shopcore", "shipstream")
    graph.add_edge("shipstream", "payguard")
    graph.add_edge("payguard", "caredesk")
    graph.add_edge("caredesk", "aggregate")
    graph.add_edge("aggregate", END)

    logger.info("Supervisor graph compiled successfully")
    return graph.compile()


SUPERVISOR_GRAPH = build_supervisor_graph()

# -------------------------------------------------------------------
# Public Runner
# -------------------------------------------------------------------

async def run_supervisor(query: str, user_email: str) -> dict:
    def _normalize_identifiers(text: str) -> str:
        t = (text or "")
        if not t:
            return t
        # Normalize unicode hyphens/dashes to ASCII '-'
        t = re.sub(r"[‐‑‒–—−]", "-", t)
        t = re.sub(r"\bF\s*W\s*D\b", "FWD", t, flags=re.IGNORECASE)
        t = re.sub(r"\bN\s*D\s*R\b", "NDR", t, flags=re.IGNORECASE)
        t = re.sub(r"\bE\s*X\s*C\b", "EXC", t, flags=re.IGNORECASE)
        t = re.sub(r"\bR\s*E\s*V\b", "REV", t, flags=re.IGNORECASE)

        def _fix(match: re.Match) -> str:
            prefix = (match.group(1) or "").upper()
            digits = re.sub(r"\D+", "", match.group(2) or "")
            if not digits:
                return match.group(0)
            return f"{prefix}-{digits}"

        t = re.sub(
            r"\b(FWD|REV|NDR|EXC)\b\s*[-#]?\s*([0-9][0-9\s]{1,10})\b",
            _fix,
            t,
            flags=re.IGNORECASE,
        )
        return t

    query = _normalize_identifiers(query)
    result = await SUPERVISOR_GRAPH.ainvoke({
        "query": query,
        "user_email": user_email,

        "shopcore_ctx": None,
        "shipstream_ctx": None,
        "payguard_ctx": None,
        "caredesk_ctx": None,

        "decision_trace": [],
        "confidence_score": 0.0,

        "final_response": None,
    })

    return {
        "answer": result["final_response"],
        "confidence": result["confidence_score"],
        "decision_trace": result["decision_trace"],
    }
