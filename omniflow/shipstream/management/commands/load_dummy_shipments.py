import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from omniflow.shipstream.models import Shipment, ReverseShipment, NdrEvent, ExchangeShipment


class Command(BaseCommand):
    help = "Load dummy shipment JSON data into the SQLite database"

    db_alias = "shipstream"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help="Optional path to dummy_shipment_data.json. Defaults to <BASE_DIR>/sql_files/dummy_shipment_data.json",
        )

    def handle(self, *args, **options):
        json_path = options.get("path")
        if json_path:
            data_path = Path(json_path)
        else:
            data_path = Path(settings.BASE_DIR) / "sql_files" / "dummy_shipment_data.json"

        if not data_path.exists():
            raise FileNotFoundError(f"Dummy shipment JSON not found: {data_path}")

        with data_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        forward = payload.get("forward_shipments", {})
        reverse = payload.get("reverse_shipments", {})
        ndr = payload.get("ndr_shipments", {})
        exchange = payload.get("exchange_shipments", {})

        with transaction.atomic(using=self.db_alias):
            self._upsert_forward_shipments(forward)
            self._upsert_reverse_shipments(reverse)
            self._upsert_ndr_events(ndr)
            self._upsert_exchange_shipments(exchange)

        self.stdout.write(self.style.SUCCESS("✅ Dummy shipment data loaded into SQLite"))

    def _derive_order_id(self, tracking_number: str) -> int | None:
        # FWD-1012 -> 1012
        try:
            return int(tracking_number.split("-")[-1])
        except Exception:
            return None

    def _upsert_forward_shipments(self, forward: dict):
        for tracking_number, row in forward.items():
            shipment_date = parse_date(row.get("date"))
            estimated_arrival = shipment_date + timedelta(days=4) if shipment_date else None

            amount = row.get("amount")
            try:
                amount_decimal = Decimal(str(amount)) if amount is not None else Decimal("0.00")
            except Exception:
                amount_decimal = Decimal("0.00")

            Shipment.objects.using(self.db_alias).update_or_create(
                tracking_number=tracking_number,
                defaults={
                    "order_id": self._derive_order_id(tracking_number),
                    "shipment_date": shipment_date,
                    "estimated_arrival": estimated_arrival,
                    "customer_name": row.get("customer", ""),
                    "status": row.get("status", ""),
                    "amount": amount_decimal,
                    "notes": row.get("notes", ""),
                },
            )

    def _upsert_reverse_shipments(self, reverse: dict):
        for reverse_number, row in reverse.items():
            original_awb = row.get("original_awb")
            if not original_awb:
                continue

            # Ensure the referenced forward shipment exists
            Shipment.objects.using(self.db_alias).get_or_create(tracking_number=original_awb)

            ReverseShipment.objects.using(self.db_alias).update_or_create(
                reverse_number=reverse_number,
                defaults={
                    "original_shipment_id": original_awb,
                    "return_date": parse_date(row.get("return_date")),
                    "reason": row.get("reason", ""),
                    "refund_status": row.get("refund_status", ""),
                },
            )

    def _upsert_ndr_events(self, ndr: dict):
        for ndr_number, row in ndr.items():
            original_awb = row.get("original_awb")
            if not original_awb:
                continue

            Shipment.objects.using(self.db_alias).get_or_create(tracking_number=original_awb)

            attempts = row.get("attempts")
            try:
                attempts_int = int(attempts) if attempts is not None else 1
            except Exception:
                attempts_int = 1

            NdrEvent.objects.using(self.db_alias).update_or_create(
                ndr_number=ndr_number,
                defaults={
                    "original_shipment_id": original_awb,
                    "ndr_date": parse_date(row.get("ndr_date")),
                    "issue": row.get("issue", ""),
                    "attempts": attempts_int,
                    "final_outcome": row.get("final_outcome", ""),
                },
            )

    def _upsert_exchange_shipments(self, exchange: dict):
        for exchange_number, row in exchange.items():
            original_awb = row.get("original_awb")
            if not original_awb:
                continue

            Shipment.objects.using(self.db_alias).get_or_create(tracking_number=original_awb)

            ExchangeShipment.objects.using(self.db_alias).update_or_create(
                exchange_number=exchange_number,
                defaults={
                    "original_shipment_id": original_awb,
                    "exchange_date": parse_date(row.get("exchange_date")),
                    "new_item": row.get("new_item", ""),
                    "status": row.get("status", ""),
                },
            )
