from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from omniflow.agents.input_data import (
    input_users_db,
    input_products_db,
    input_orders_db,
    input_forward_shipments_db,
    input_reverse_shipments_db,
    input_ndr_shipments_db,
    input_exchange_shipments_db,
    input_payments_db,
    input_tickets_db,
)

from omniflow.shopcore.models import User, Product, Order
from omniflow.shipstream.models import (
    Shipment,
    ReverseShipment,
    NdrEvent,
    ExchangeShipment,
    TrackingEvent,
    Warehouse,
)
from omniflow.caredesk.models import Ticket, TicketMessage
from omniflow.payguard.models import Wallet, PaymentMethod, Transaction


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


def _derive_order_id_from_shipment_id(shipment_id: str | None) -> int | None:
    # FWD-1001 -> 1001
    if not shipment_id:
        return None
    try:
        return int(str(shipment_id).split("-")[-1])
    except Exception:
        return None


def _derive_ticket_pk(ticket_key: str) -> int | None:
    # TKT-1001 -> 1001
    try:
        return int(str(ticket_key).split("-")[-1])
    except Exception:
        return None


class Command(BaseCommand):
    help = "Seed all domain databases from omniflow/agents/input_data.py"

    def handle(self, *args, **options):
        now = timezone.now()

        # -----------------------------
        # ShopCore
        # -----------------------------
        with transaction.atomic(using="shopcore"):
            for _, row in (input_users_db or {}).items():
                uid = row.get("id")
                email = (row.get("email") or "").strip().lower() or None
                name = (row.get("name") or "").strip()
                if not uid:
                    continue

                User.objects.using("shopcore").update_or_create(
                    id=int(uid),
                    defaults={
                        "name": name or f"User {uid}",
                        "email": email,
                        "premium_status": bool(row.get("premium_status") or False),
                    },
                )

            for _, row in (input_products_db or {}).items():
                pid = row.get("id")
                if not pid:
                    continue

                price = row.get("price")
                try:
                    price_dec = Decimal(str(price)) if price is not None else Decimal("0.00")
                except Exception:
                    price_dec = Decimal("0.00")

                Product.objects.using("shopcore").update_or_create(
                    id=int(pid),
                    defaults={
                        "name": (row.get("name") or "").strip() or f"Product {pid}",
                        "category": (row.get("category") or "").strip() or "Unknown",
                        "price": price_dec,
                    },
                )

            for _, row in (input_orders_db or {}).items():
                shipment_id = row.get("shipment_id")
                oid = _derive_order_id_from_shipment_id(shipment_id)
                if not oid:
                    continue

                user_id = row.get("user_id")
                product_id = row.get("product_id")
                order_date = _parse_date(row.get("order_date")) or now.date()
                status = (row.get("status") or "Processing").strip() or "Processing"

                Order.objects.using("shopcore").update_or_create(
                    id=int(oid),
                    defaults={
                        "user_id": int(user_id) if user_id is not None else None,
                        "product_id": int(product_id) if product_id is not None else None,
                        "order_date": order_date,
                        "status": status,
                    },
                )

                if user_id is not None and product_id is not None:
                    qs = (
                        Order.objects.using("shopcore")
                        .filter(user_id=int(user_id), product_id=int(product_id))
                        .exclude(id=int(oid))
                    )
                    try:
                        qs._raw_delete(using="shopcore")
                    except Exception:
                        from django.db import connections

                        with connections["shopcore"].cursor() as cursor:
                            cursor.execute(
                                "DELETE FROM shopcore_order WHERE user_id = ? AND product_id = ? AND id <> ?",
                                [int(user_id), int(product_id), int(oid)],
                            )

        # -----------------------------
        # ShipStream
        # -----------------------------
        with transaction.atomic(using="shipstream"):
            # Warehouses used for tracking events
            wh_origin, _ = Warehouse.objects.using("shipstream").get_or_create(
                location="Origin Hub",
                defaults={"manager_name": "Manager Origin"},
            )
            wh_transit, _ = Warehouse.objects.using("shipstream").get_or_create(
                location="Transit Hub",
                defaults={"manager_name": "Manager Transit"},
            )
            wh_dest, _ = Warehouse.objects.using("shipstream").get_or_create(
                location="Destination Hub",
                defaults={"manager_name": "Manager Destination"},
            )

            for tracking_number, row in (input_forward_shipments_db or {}).items():
                tn = (tracking_number or "").strip().upper()
                if not tn:
                    continue

                shipment_date = _parse_date(row.get("date"))
                eta = shipment_date + timedelta(days=4) if shipment_date else None

                amount = row.get("amount")
                try:
                    amount_dec = Decimal(str(amount)) if amount is not None else Decimal("0.00")
                except Exception:
                    amount_dec = Decimal("0.00")

                order_id = _derive_order_id_from_shipment_id(tn)

                shipment, _ = Shipment.objects.using("shipstream").update_or_create(
                    tracking_number=tn,
                    defaults={
                        "order_id": int(order_id) if order_id is not None else None,
                        "shipment_date": shipment_date,
                        "estimated_arrival": eta,
                        "customer_name": (row.get("customer") or "").strip(),
                        "status": (row.get("status") or "").strip(),
                        "amount": amount_dec,
                        "notes": (row.get("notes") or "").strip(),
                    },
                )

                # Minimal tracking timeline for current-location support.
                # Idempotent: remove previous synthetic events for this shipment.
                TrackingEvent.objects.using("shipstream").filter(
                    shipment_id=shipment.id,
                    status_update__in=["Created", "In Transit", "Delivered", "RTO_Initiated", "Exchanged"],
                ).delete()

                status = (shipment.status or "").strip()
                if status == "Delivered":
                    wid = wh_dest.id
                elif status == "RTO_Initiated":
                    wid = wh_transit.id
                elif status == "Exchanged":
                    wid = wh_dest.id
                else:
                    wid = wh_transit.id

                TrackingEvent.objects.using("shipstream").create(
                    shipment_id=shipment.id,
                    warehouse_id=int(wid),
                    timestamp=now,
                    status_update=status or "In Transit",
                )

            for reverse_number, row in (input_reverse_shipments_db or {}).items():
                rn = (reverse_number or "").strip().upper()
                original_awb = (row.get("original_awb") or "").strip().upper()
                if not rn or not original_awb:
                    continue

                Shipment.objects.using("shipstream").get_or_create(tracking_number=original_awb)

                ReverseShipment.objects.using("shipstream").update_or_create(
                    reverse_number=rn,
                    defaults={
                        "original_shipment_id": original_awb,
                        "return_date": _parse_date(row.get("return_date")) or now.date(),
                        "reason": (row.get("reason") or "").strip(),
                        "refund_status": (row.get("refund_status") or "").strip(),
                    },
                )

            for ndr_number, row in (input_ndr_shipments_db or {}).items():
                nn = (ndr_number or "").strip().upper()
                original_awb = (row.get("original_awb") or "").strip().upper()
                if not nn or not original_awb:
                    continue

                Shipment.objects.using("shipstream").get_or_create(tracking_number=original_awb)

                attempts = row.get("attempts")
                try:
                    attempts_int = int(attempts) if attempts is not None else 1
                except Exception:
                    attempts_int = 1

                NdrEvent.objects.using("shipstream").update_or_create(
                    ndr_number=nn,
                    defaults={
                        "original_shipment_id": original_awb,
                        "ndr_date": _parse_date(row.get("ndr_date")) or now.date(),
                        "issue": (row.get("issue") or "").strip(),
                        "attempts": attempts_int,
                        "final_outcome": (row.get("final_outcome") or "").strip(),
                    },
                )

            for exchange_number, row in (input_exchange_shipments_db or {}).items():
                en = (exchange_number or "").strip().upper()
                original_awb = (row.get("original_awb") or "").strip().upper()
                if not en or not original_awb:
                    continue

                Shipment.objects.using("shipstream").get_or_create(tracking_number=original_awb)

                ExchangeShipment.objects.using("shipstream").update_or_create(
                    exchange_number=en,
                    defaults={
                        "original_shipment_id": original_awb,
                        "exchange_date": _parse_date(row.get("exchange_date")) or now.date(),
                        "new_item": (row.get("new_item") or "").strip(),
                        "status": (row.get("status") or "").strip(),
                    },
                )

        # -----------------------------
        # CareDesk
        # -----------------------------
        with transaction.atomic(using="caredesk"):
            for ticket_key, row in (input_tickets_db or {}).items():
                pk = _derive_ticket_pk(ticket_key)
                if not pk:
                    continue

                user_id = row.get("user_id")
                user_email = (row.get("user_email") or "").strip().lower()

                # If we have an order for the same user+Gaming Monitor in input_orders_db, reference it.
                ref = None
                for _, o in (input_orders_db or {}).items():
                    if o.get("user_id") == user_id:
                        ref = _derive_order_id_from_shipment_id(o.get("shipment_id"))
                        if ref:
                            break

                Ticket.objects.using("caredesk").update_or_create(
                    id=int(pk),
                    defaults={
                        "user_id": int(user_id) if user_id is not None else 0,
                        "reference_id": str(ref) if ref is not None else (user_email or ""),
                        "issue_type": (row.get("subject") or "").strip() or "Support",
                        "status": (row.get("status") or "").strip() or "Open",
                    },
                )

                if not TicketMessage.objects.using("caredesk").filter(ticket_id=int(pk)).exists():
                    TicketMessage.objects.using("caredesk").create(
                        ticket_id=int(pk),
                        sender="Agent",
                        content="Seeded from input_data.",
                    )

        # -----------------------------
        # PayGuard
        # -----------------------------
        with transaction.atomic(using="payguard"):
            # Wallets for all users in input_data
            for _, row in (input_users_db or {}).items():
                uid = row.get("id")
                if not uid:
                    continue

                Wallet.objects.using("payguard").update_or_create(
                    user_id=int(uid),
                    defaults={
                        "balance": Decimal("0.00"),
                        "currency": "INR",
                    },
                )

            # Create one payment method per wallet if missing
            for wallet in Wallet.objects.using("payguard").all():
                if not PaymentMethod.objects.using("payguard").filter(wallet_id=wallet.id).exists():
                    PaymentMethod.objects.using("payguard").create(
                        wallet=wallet,
                        provider="VISA",
                        expiry_date=(now.date() + timedelta(days=365 * 2)),
                    )

            # Transactions based on input_payments_db
            for _, row in (input_payments_db or {}).items():
                ext_order = row.get("order_id")
                amount = row.get("amount")
                status = (row.get("status") or "").strip().lower()

                # Map external order string -> derived int order_id
                order_id = None
                if isinstance(ext_order, str):
                    order_row = (input_orders_db or {}).get(ext_order)
                    if isinstance(order_row, dict):
                        order_id = _derive_order_id_from_shipment_id(order_row.get("shipment_id"))
                if order_id is None:
                    continue

                # Find user_id from order
                user_id = None
                for _, o in (input_orders_db or {}).items():
                    if _derive_order_id_from_shipment_id(o.get("shipment_id")) == order_id:
                        user_id = o.get("user_id")
                        break
                if user_id is None:
                    continue

                wallet = Wallet.objects.using("payguard").filter(user_id=int(user_id)).first()
                if not wallet:
                    continue

                try:
                    amount_dec = Decimal(str(amount)) if amount is not None else Decimal("0.00")
                except Exception:
                    amount_dec = Decimal("0.00")

                tx_type = "Debit" if status == "paid" else "Refund" if status == "refunded" else "Debit"

                Transaction.objects.using("payguard").create(
                    wallet=wallet,
                    order_id=int(order_id),
                    amount=amount_dec,
                    type=tx_type,
                )

        self.stdout.write(self.style.SUCCESS("✅ Seeded all domain DBs from input_data.py"))
