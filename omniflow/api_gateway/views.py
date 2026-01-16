import asyncio
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db import close_old_connections
import re
import time
import secrets
from datetime import date

from omniflow.core.orchestration.supervisor_graph import run_supervisor
from omniflow.utils.logging import get_logger

from omniflow.shipstream.models import Shipment, ReverseShipment
from omniflow.shopcore.models import User, Order
from omniflow.caredesk.models import Ticket, TicketAttachment
from omniflow.payguard.models import Wallet, Transaction

logger = get_logger(__name__)

# ---------------------------------------------------------------------
# Utilities (ONLY deterministic helpers remain)
# ---------------------------------------------------------------------

TRACKING_REGEX = re.compile(r"\b(FWD|REV|NDR|EXC)\s*[-#]?\s*(\d+)\b", re.IGNORECASE)

# Keywords that indicate data access requests
DATA_ACCESS_KEYWORDS = [
    "track", "tracking", "shipment", "order", "return", "refund", "ndr", "exchange", "wallet", "balance", "payment", "transaction"
]

def is_data_access_request(query: str) -> bool:
    q = query.lower()
    return any(keyword in q for keyword in DATA_ACCESS_KEYWORDS)

def get_user_from_session(user_email: str) -> User | None:
    # Try to fetch user by email; if not found, return None
    return User.objects.filter(email=user_email).first()

def normalize_query(q: str) -> str:
    if not q:
        return ""
    q = re.sub(r"[‐‑‒–—−]", "-", q)
    # Normalize spaced formats like "FWD 1001" -> "FWD-1001"
    q = re.sub(r"\b(FWD|REV|NDR|EXC)\s+(\d+)\b", r"\1-\2", q, flags=re.IGNORECASE)
    # Also normalize "FWD1001" -> "FWD-1001"
    q = re.sub(r"\b(FWD|REV|NDR|EXC)(\d+)\b", r"\1-\2", q, flags=re.IGNORECASE)
    return q

def extract_tracking_id(q: str) -> str | None:
    if not q:
        return None
    m = TRACKING_REGEX.search(q)
    if m:
        prefix = m.group(1).upper()
        number = m.group(2)
        return f"{prefix}-{number}"
    # Fallback: brute-force scan for any FWD/REV/NDR/EXC followed by digits
    fallback = re.search(r"\b(FWD|REV|NDR|EXC)[\s#-]*(\d+)\b", q, flags=re.IGNORECASE)
    if fallback:
        prefix = fallback.group(1).upper()
        number = fallback.group(2)
        logger.info(f"[DEBUG] fallback matched: prefix={prefix} number={number}")
        return f"{prefix}-{number}"
    logger.info(f"[DEBUG] no tracking ID found in: {q!r}")
    return None

# ---------------------------------------------------------------------
# API VIEW
# ---------------------------------------------------------------------

@method_decorator(csrf_exempt, name="dispatch")
class QueryAPIView(APIView):
    def post(self, request):
        close_old_connections()

        query = request.data.get("query", "")
        user_email = request.data.get("user_email")

        if not user_email:
            return Response(
                {"error": "user_email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        query = normalize_query(query)
        tracking_id = extract_tracking_id(query)

        # DEBUG LOG
        logger.info(f"[DEBUG] query={query!r} tracking_id={tracking_id!r}")

        # ===============================================================
        # FIRST MESSAGE: backend greeting on empty query
        # ===============================================================
        if not query:
            return Response({
                "response": {
                    "answer": "Hello! I'm OmniFlow, your intelligent retail assistant. I can help you with order status, shipment tracking, payments, returns, refunds, NDRs, and exchanges. How can I assist you today?",
                    "confidence": 1.0,
                    "decision_trace": [{"agent": "System", "reason": "Initial greeting"}],
                }
            }, status=status.HTTP_200_OK)

        # ===============================================================
        # 🔐 IDENTITY CHECK: Require name before accessing any data
        # ===============================================================
        user = get_user_from_session(user_email)
        session_key = f"identified_user_{user_email}"
        identified = request.session.get(session_key, False)

        if is_data_access_request(query) and not identified:
            # Ask for the user's name to verify identity
            if not user or not user.name:
                return Response({
                    "response": {
                        "answer": "To access your order or shipment information, please tell me your full name so I can verify your identity.",
                        "confidence": 0.9,
                        "decision_trace": [{"agent": "System", "reason": "Identity required: name missing"}],
                    }
                }, status=status.HTTP_200_OK)

            # If we have a name, ask user to confirm it
            return Response({
                "response": {
                    "answer": f"To proceed, please confirm: Are you {user.name}? (yes/no)",
                    "confidence": 0.9,
                    "decision_trace": [{"agent": "System", "reason": "Identity confirmation required"}],
                }
            }, status=status.HTTP_200_OK)

        # Handle identity confirmation
        if is_data_access_request(query) and "yes" in query.lower() and user and user.name:
            request.session[session_key] = True
            request.session.save()
            return Response({
                "response": {
                    "answer": "Thank you! Your identity is confirmed. Please provide your order ID, tracking number, or tell me how I can help you today.",
                    "confidence": 0.95,
                    "decision_trace": [{"agent": "System", "reason": "Identity confirmed"}],
                }
            }, status=status.HTTP_200_OK)

        # ===============================================================
        # 🔐 HARD RULE: TRACKING IS ALWAYS DETERMINISTIC
        # ===============================================================
        if tracking_id and identified:
            try:
                # 🔒 Bypass intent + smalltalk + LLM
                # Supervisor will ONLY resolve, never ask questions
                result = asyncio.run(run_supervisor(
                    query=tracking_id,
                    user_email=user_email
                ))

                answer = result.get("answer")

                # Absolute guard: NEVER ask for tracking again
                if not answer or "provide" in answer.lower():
                    return Response({
                        "response": {
                            "answer": f"{tracking_id} could not be found. Please verify the ID and try again.",
                            "confidence": 0.7,
                            "decision_trace": [{
                                "agent": "ShipStream",
                                "reason": "Deterministic tracking lookup"
                            }]
                        }
                    }, status=status.HTTP_200_OK)

                return Response(
                    {"response": result},
                    status=status.HTTP_200_OK
                )

            except Exception as e:
                logger.error(f"Tracking failed: {e}", exc_info=True)
                return Response({
                    "response": {
                        "answer": "Unable to retrieve tracking information at the moment.",
                        "confidence": 0.6,
                        "decision_trace": [{
                            "agent": "ShipStream",
                            "reason": "Exception"
                        }]
                    }
                }, status=status.HTTP_200_OK)

        # ===============================================================
        # PAYGUARD (deterministic, identity required)
        # ===============================================================
        if ("wallet" in query.lower() or "balance" in query.lower()) and identified:
            user = get_user_from_session(user_email)
            if not user:
                return Response({
                    "response": {
                        "answer": "Please identify yourself before accessing wallet details.",
                        "confidence": 0.8,
                        "decision_trace": [{"agent": "ShopCore", "reason": "Identity missing"}],
                    }
                }, status=status.HTTP_200_OK)

            wallet = Wallet.objects.filter(user_id=user.id).first()
            if not wallet:
                return Response({
                    "response": {
                        "answer": "No wallet found for your account.",
                        "confidence": 0.8,
                        "decision_trace": [{"agent": "PayGuard", "reason": "Wallet missing"}],
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "response": {
                    "answer": f"Your wallet balance is {wallet.balance} {wallet.currency}.",
                    "confidence": 0.9,
                    "decision_trace": [{"agent": "PayGuard", "reason": "Wallet lookup"}],
                }
            }, status=status.HTTP_200_OK)

        # ===============================================================
        # FALLBACK → SUPERVISOR (non-tracking only)
        # ===============================================================
        try:
            result = asyncio.run(run_supervisor(
                query=query,
                user_email=user_email
            ))
            return Response(
                {"response": result},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return Response({
                "response": {
                    "answer": "Sorry — something went wrong.",
                    "confidence": 0.5,
                    "decision_trace": [{"agent": "System", "reason": "Unhandled exception"}],
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

def omni_ui(request):
    logger.info("Rendering OmniFlow UI")
    return render(request, "omni_ui.html")
