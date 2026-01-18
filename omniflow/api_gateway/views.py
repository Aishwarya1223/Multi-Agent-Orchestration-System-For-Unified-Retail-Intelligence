# api_gateway/views.py
import asyncio
import json
import re
import sys

from asgiref.sync import async_to_sync
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import close_old_connections

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from langchain_core.messages import SystemMessage, HumanMessage

from omniflow.core.orchestration.supervisor_graph import run_supervisor
from omniflow.agents.langchain_based_agents.base import get_llm
from omniflow.utils.logging import get_logger
from omniflow.utils.prompts import get_ask_name_prompt, get_response_synthesizer_prompt

from omniflow.shopcore.models import User
from omniflow.payguard.models import Wallet
from omniflow.shipstream.models import Shipment
from omniflow.agents.input_data import input_orders_db

logger = get_logger(__name__)

# ---------------------------------------------------------------------
# LLM helper (phrasing ONLY)
# ---------------------------------------------------------------------

def _llm_reply(system_instruction: str, user_message: str = "") -> str:
    llm = get_llm()
    out = llm.invoke([
        SystemMessage(content=system_instruction),
        HumanMessage(content=user_message),
    ])
    return (getattr(out, "content", "") or "").strip()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

TRACKING_REGEX = re.compile(r"\b(FWD|REV|NDR|EXC)[- ]*(\d+)\b", re.I)
ORDER_REF_REGEX = re.compile(r"\bORD-\d{4}-\d+\b", re.I)
ORDER_ID_REGEX = re.compile(r"\border\s*(\d{3,})\b", re.I)

ACCOUNT_KEYWORDS = {"wallet", "balance", "payment", "transactions", "account"}
SHIPMENT_KEYWORDS = {"track", "shipment", "delivery", "return", "refund", "ndr", "exchange"}


def normalize_query(q: str) -> str:
    if not q:
        return ""
    q = re.sub(r"[‐-‒–—−]", "-", q)
    q = re.sub(r"\b(FWD|REV|NDR|EXC)\s*(\d+)\b", r"\1-\2", q, flags=re.I)
    return q.strip()


def extract_tracking_id(q: str) -> str | None:
    m = TRACKING_REGEX.search(q or "")
    if not m:
        return None
    return f"{m.group(1).upper()}-{m.group(2)}"


def extract_order_ref(q: str) -> str | None:
    m = ORDER_REF_REGEX.search(q or "")
    return m.group(0).upper() if m else None


def extract_order_id_int(q: str) -> int | None:
    m = ORDER_ID_REGEX.search(q or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def derive_order_id_from_tracking(tracking_number: str | None) -> int | None:
    if not tracking_number:
        return None
    try:
        return int(str(tracking_number).split("-")[-1])
    except Exception:
        return None


def is_account_query(q: str) -> bool:
    q = q.lower()
    return any(k in q for k in ACCOUNT_KEYWORDS)


def is_shipment_query(q: str) -> bool:
    q = q.lower()
    return any(k in q for k in SHIPMENT_KEYWORDS)


def is_valid_user_name(value: str) -> bool:
    v = (value or "").strip()
    if not v:
        return False
    if len(v) < 2 or len(v) > 60:
        return False
    if v.strip().lower() in {"hi", "hello", "hey"}:
        return False
    if TRACKING_REGEX.search(v):
        return False
    if any(ch.isdigit() for ch in v):
        return False
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", v):
        return False
    return True


def extract_name_candidate(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"\bmy\s+name\s+is\s+(.+)$", t, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bi\s+am\s+(.+)$", t, re.I)
    if m:
        return m.group(1).strip()
    return t


def get_user(email: str) -> User | None:
    return User.objects.filter(email=email).first()


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------

@method_decorator(csrf_exempt, name="dispatch")
class QueryAPIView(APIView):

    def post(self, request):
        close_old_connections()

        raw_query = request.data.get("query", "")
        action_tracking_number = request.data.get("tracking_number")
        reference_id = request.data.get("reference_id")
        image = request.data.get("image")
        user_email = request.data.get("user_email")

        if not user_email:
            return Response({"error": "user_email is required"}, status=400)

        query = normalize_query(raw_query)
        extracted_tracking = extract_tracking_id(query)
        extracted_order_ref = extract_order_ref(query)
        extracted_order_id = extract_order_id_int(query)

        if not extracted_tracking and extracted_order_ref:
            row = (input_orders_db or {}).get(extracted_order_ref)
            shipment_id = (row or {}).get("shipment_id")
            if shipment_id:
                extracted_tracking = normalize_query(str(shipment_id))
            if extracted_order_id is None and shipment_id:
                extracted_order_id = derive_order_id_from_tracking(str(shipment_id))

        if not extracted_tracking and extracted_order_id:
            shipment = (
                Shipment.objects.using("shipstream")
                .filter(order_id=int(extracted_order_id))
                .order_by("-id")
                .first()
            )
            if shipment and shipment.tracking_number:
                extracted_tracking = shipment.tracking_number

        if extracted_order_id is None and extracted_tracking:
            extracted_order_id = derive_order_id_from_tracking(extracted_tracking)

        logger.info(
            f"[QUERY] {query!r} | extracted_tracking={extracted_tracking} | extracted_order_ref={extracted_order_ref} | extracted_order_id={extracted_order_id}"
        )

        # --------------------------------------------------
        # Session keys
        # --------------------------------------------------

        name_key = f"user_name_{user_email}"
        tracking_key = f"user_tracking_{user_email}"
        pending_key = f"pending_action_{user_email}"
        name_pending_key = f"user_name_pending_{user_email}"
        order_id_key = f"user_order_id_{user_email}"
        order_ref_key = f"user_order_ref_{user_email}"

        user_name = request.session.get(name_key)
        stored_tracking = request.session.get(tracking_key)
        stored_order_id = request.session.get(order_id_key)
        stored_order_ref = request.session.get(order_ref_key)
        pending_action = request.session.get(pending_key)
        name_pending = bool(request.session.get(name_pending_key))

        if extracted_order_id is not None:
            request.session[order_id_key] = int(extracted_order_id)
            stored_order_id = int(extracted_order_id)
            request.session.save()

        if extracted_order_ref:
            request.session[order_ref_key] = extracted_order_ref
            stored_order_ref = extracted_order_ref
            request.session.save()

        if user_name is not None and not is_valid_user_name(str(user_name)):
            request.session[name_key] = None
            request.session[name_pending_key] = False
            request.session.save()
            user_name = None

        # If the user explicitly refers to a different tracking ID, do not let an old
        # pending action leak into this turn.
        if extracted_tracking and pending_action:
            if not isinstance(pending_action, dict):
                pending_action = None
                request.session[pending_key] = None
                request.session.save()
            else:
                pending_tracking = (pending_action.get("tracking_number") or "").strip().upper() or None
                if pending_tracking and extracted_tracking != pending_tracking:
                    pending_action = None
                    request.session[pending_key] = None
                    request.session.save()

        # --------------------------------------------------
        # Action payload support (from UI)
        # --------------------------------------------------
        action_tracking = (action_tracking_number or "").strip().upper() or None
        if action_tracking and not extracted_tracking:
            request.session[tracking_key] = action_tracking
            stored_tracking = action_tracking
            request.session.save()

        if query in {"confirm_return", "cancel_return"}:
            tracking_for_action = extracted_tracking or stored_tracking
            if tracking_for_action:
                pending_action = {
                    "action": "confirm_return",
                    "tracking_number": tracking_for_action,
                }
                # Supervisor expects YES/NO text while pending_action=confirm_return is set.
                query = "YES" if query == "confirm_return" else "NO"

        # --------------------------------------------------
        # Greeting
        # --------------------------------------------------

        if not query and not image and not reference_id:
            request.session[name_key] = None
            request.session[name_pending_key] = False
            request.session.save()
            return Response({
                "response": {
                    "answer": _llm_reply(
                        "You are OmniFlow, a friendly retail assistant and first introduce yourself what you can do.",
                        "Greet the user and ask how you can help."
                    ),
                    "confidence": 1.0,
                    "decision_trace": [{"agent": "System", "reason": "Greeting"}],
                }
            })

        # --------------------------------------------------
        # Store tracking ONLY if present now
        # --------------------------------------------------

        if extracted_tracking:
            request.session[tracking_key] = extracted_tracking
            stored_tracking = extracted_tracking
            request.session.save()

        # --------------------------------------------------
        # Ask name ONLY for account queries
        # --------------------------------------------------

        if request.session.get(name_pending_key):
            request.session[name_pending_key] = False
            request.session.save()

        if is_account_query(query) and any(k in query.lower() for k in ["wallet", "balance"]):
            user = get_user(user_email)
            wallet = (
                Wallet.objects.using("payguard").filter(user_id=user.id).first()
                if user
                else None
            )

            if wallet:
                facts = {
                    "payguard": {
                        "balance": str(wallet.balance),
                        "currency": wallet.currency,
                    }
                }

                prompt = get_response_synthesizer_prompt()
                msg = (
                    "USER_MESSAGE:\n"
                    f"{query}\n\n"
                    "FACTS_JSON:\n"
                    f"{json.dumps(facts, ensure_ascii=False)}"
                )

                answer = _llm_reply(prompt, msg)

                return Response({
                    "response": {
                        "answer": answer,
                        "confidence": 0.95,
                        "decision_trace": [
                            {"agent": "PayGuard", "reason": "Wallet data retrieved"},
                            {"agent": "LLM", "reason": "Response synthesized"},
                        ],
                        "facts": facts,
                    }
                })

        supervisor_query = query

        # If the user provided an order reference/id (e.g., "ORD-2026-001" or "order 1001")
        # and we could resolve it to a shipment tracking number, but they didn't specify
        # an explicit action, default to tracking so we return something useful.
        if (
            extracted_tracking
            and (extracted_order_ref or extracted_order_id)
            and not is_shipment_query(query)
            and not is_account_query(query)
        ):
            supervisor_query = f"track {extracted_tracking}"

        # Follow-up queries like "what is the price I paid for the order?" should reuse
        # the last known order context if present.
        lower_q = (query or "").lower()
        asks_paid = any(k in lower_q for k in ["paid", "price", "how much", "amount", "cost"])
        refers_to_order = "order" in lower_q
        if (
            stored_order_id
            and asks_paid
            and refers_to_order
            and extracted_order_id is None
            and not extracted_order_ref
            and not extracted_tracking
        ):
            supervisor_query = f"{query} order {int(stored_order_id)}"

        if is_shipment_query(query) and stored_tracking and not extracted_tracking:
            lower_q = (query or "").lower()
            wants_return = any(k in lower_q for k in ["return", "refund", "send back"])
            if wants_return:
                supervisor_query = f"return {stored_tracking}"
            else:
                supervisor_query = f"track {stored_tracking}"

        # --------------------------------------------------
        # Supervisor call
        # --------------------------------------------------

        try:
            if getattr(sys, "is_finalizing", None) and sys.is_finalizing():
                return Response({
                    "response": {
                        "answer": "The server is restarting. Please try your request again in a moment.",
                        "confidence": 0.4,
                        "decision_trace": [{"agent": "System", "reason": "Server restarting"}],
                    }
                })

            try:
                result = asyncio.run(run_supervisor(
                    query=supervisor_query,
                    user_email=user_email,
                    user_name=user_name,
                    pending_action=pending_action,
                    image=image,
                    reference_id=reference_id,
                ))
            except RuntimeError as e:
                msg = str(e) if e else ""
                if "asyncio.run() cannot be called" in msg or "running event loop" in msg:
                    result = async_to_sync(run_supervisor)(
                        query=supervisor_query,
                        user_email=user_email,
                        user_name=user_name,
                        pending_action=pending_action,
                        image=image,
                        reference_id=reference_id,
                    )
                else:
                    raise

            request.session[pending_key] = result.get("pending_action")
            request.session.save()

            # Trust supervisor output
            return Response({"response": result})

        except RuntimeError as e:
            msg = str(e) if e else ""
            if "interpreter shutdown" in msg or "cannot schedule new futures" in msg:
                logger.warning("Supervisor skipped during shutdown", exc_info=True)
                return Response({
                    "response": {
                        "answer": "The server is restarting. Please try your request again in a moment.",
                        "confidence": 0.4,
                        "decision_trace": [{"agent": "System", "reason": "Server restarting"}],
                    }
                })
            logger.error("Supervisor failed", exc_info=True)
            return Response({
                "response": {
                    "answer": "Sorry — something went wrong while processing your request. Please try again.",
                    "confidence": 0.5,
                    "decision_trace": [{"agent": "System", "reason": "Exception"}],
                }
            })

        except Exception:
            msg = ""
            try:
                msg = str(getattr(sys, "exc_info")()[1] or "")
            except Exception:
                msg = ""
            if "interpreter shutdown" in msg or "cannot schedule new futures" in msg:
                logger.warning("Supervisor skipped during shutdown", exc_info=True)
                return Response({
                    "response": {
                        "answer": "The server is restarting. Please try your request again in a moment.",
                        "confidence": 0.4,
                        "decision_trace": [{"agent": "System", "reason": "Server restarting"}],
                    }
                })
            logger.error("Supervisor failed", exc_info=True)
            return Response({
                "response": {
                    "answer": "Sorry — something went wrong while processing your request. Please try again.",
                    "confidence": 0.5,
                    "decision_trace": [{"agent": "System", "reason": "Exception"}],
                }
            })


def omni_ui(request):
    logger.info("Rendering OmniFlow UI")
    return render(request, "omni_ui.html")
