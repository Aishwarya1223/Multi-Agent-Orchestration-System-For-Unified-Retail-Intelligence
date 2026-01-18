from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from omniflow.shopcore.models import User, Product, Order
from omniflow.shipstream.models import Shipment, TrackingEvent, Warehouse
from omniflow.caredesk.models import Ticket, TicketMessage


class Command(BaseCommand):
    help = (
        "Seed demo data for the 3-domain complex query workflow: "
        "ShopCore(order/product) + ShipStream(tracking events/location) + CareDesk(ticket status)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user_email", default="test@omni.com")
        parser.add_argument("--user_name", default="Test User")
        parser.add_argument("--product_name", default="Gaming Monitor")
        parser.add_argument("--order_id", type=int, default=1001)
        parser.add_argument("--tracking_number", default="FWD-1001")
        parser.add_argument("--ticket_status", default="Assigned")

    def handle(self, *args, **options):
        user_email = str(options.get("user_email") or "test@omni.com").strip().lower()
        user_name = str(options.get("user_name") or "Test User").strip()
        product_name = str(options.get("product_name") or "Gaming Monitor").strip()
        order_id = int(options.get("order_id") or 1001)
        tracking_number = str(options.get("tracking_number") or "FWD-1001").strip().upper()
        ticket_status = str(options.get("ticket_status") or "Assigned").strip()

        now = timezone.now()

        # -----------------------------
        # ShopCore: user + product + order
        # -----------------------------
        with transaction.atomic(using="shopcore"):
            user = User.objects.using("shopcore").filter(email__iexact=user_email).first()
            if not user:
                user = User.objects.using("shopcore").create(
                    name=user_name,
                    email=user_email,
                    premium_status=False,
                )
            else:
                updated_fields = []
                if user_name and user.name != user_name:
                    user.name = user_name
                    updated_fields.append("name")
                if user.email != user_email:
                    user.email = user_email
                    updated_fields.append("email")
                if updated_fields:
                    user.save(update_fields=updated_fields, using="shopcore")

            product = Product.objects.using("shopcore").filter(name__iexact=product_name).first()
            if not product:
                product = Product.objects.using("shopcore").create(
                    name=product_name,
                    category="Electronics",
                    price=Decimal("1200.00"),
                )

            order = Order.objects.using("shopcore").filter(id=order_id).first()
            if not order:
                order = Order.objects.using("shopcore").create(
                    id=order_id,
                    user_id=user.id,
                    product_id=product.id,
                    order_date=(now.date() - timedelta(days=7)),
                    status="Processing",
                )
            else:
                order.user_id = user.id
                order.product_id = product.id
                order.save(update_fields=["user", "product"], using="shopcore")

        # -----------------------------
        # ShipStream: shipment + warehouses + tracking events
        # -----------------------------
        with transaction.atomic(using="shipstream"):
            shipment = Shipment.objects.using("shipstream").filter(tracking_number__iexact=tracking_number).first()
            if not shipment:
                shipment = Shipment.objects.using("shipstream").create(
                    tracking_number=tracking_number,
                    order_id=order_id,
                    shipment_date=(now.date() - timedelta(days=6)),
                    estimated_arrival=(now.date() - timedelta(days=2)),
                    customer_name=user_name,
                    status="In Transit",
                    amount=Decimal("1200.00"),
                    notes="Demo: complex-query shipment",
                )
            else:
                shipment.order_id = order_id
                shipment.customer_name = user_name
                shipment.status = "In Transit"
                shipment.save(update_fields=["order", "customer_name", "status"], using="shipstream")

            wh1, _ = Warehouse.objects.using("shipstream").get_or_create(
                location="Mumbai Hub",
                defaults={"manager_name": "Manager A"},
            )
            wh2, _ = Warehouse.objects.using("shipstream").get_or_create(
                location="Bengaluru Hub",
                defaults={"manager_name": "Manager B"},
            )

            # Idempotent: clear existing demo events for this shipment (only our known statuses)
            TrackingEvent.objects.using("shipstream").filter(
                shipment_id=shipment.id,
                status_update__in=[
                    "Order packed",
                    "Picked up",
                    "In transit",
                    "Arrived at hub",
                    "Out for delivery",
                ],
            ).delete()

            events = [
                (now - timedelta(days=6, hours=2), wh1.id, "Order packed"),
                (now - timedelta(days=6), wh1.id, "Picked up"),
                (now - timedelta(days=4), wh1.id, "In transit"),
                (now - timedelta(days=2), wh2.id, "Arrived at hub"),
                (now - timedelta(hours=5), wh2.id, "Out for delivery"),
            ]
            for ts, wid, status in events:
                TrackingEvent.objects.using("shipstream").create(
                    shipment_id=shipment.id,
                    warehouse_id=int(wid),
                    timestamp=ts,
                    status_update=status,
                )

        # -----------------------------
        # CareDesk: ticket (assigned) linked to order_id + user_id
        # -----------------------------
        with transaction.atomic(using="caredesk"):
            ref = str(order_id)
            ticket = (
                Ticket.objects.using("caredesk")
                .filter(user_id=int(user.id), reference_id=ref)
                .order_by("-created_at", "-id")
                .first()
            )
            if not ticket:
                ticket = Ticket.objects.using("caredesk").create(
                    user_id=int(user.id),
                    reference_id=ref,
                    issue_type="Order Delivery Issue",
                    status=ticket_status,
                )
            else:
                ticket.status = ticket_status
                ticket.save(update_fields=["status"], using="caredesk")

            if not TicketMessage.objects.using("caredesk").filter(ticket_id=ticket.id).exists():
                TicketMessage.objects.using("caredesk").create(
                    ticket_id=ticket.id,
                    sender="Agent",
                    content="We’ve assigned your ticket to a support agent and are checking with the courier.",
                )

        self.stdout.write(
            self.style.SUCCESS(
                "✅ Seeded complex-query demo data: "
                f"user_email={user_email} order_id={order_id} tracking_number={tracking_number} ticket_status={ticket_status}"
            )
        )
