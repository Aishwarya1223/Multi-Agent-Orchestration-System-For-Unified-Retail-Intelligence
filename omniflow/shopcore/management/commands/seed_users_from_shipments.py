import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from omniflow.shopcore.models import User


class Command(BaseCommand):
    help = "Seed ShopCore users from ShipStream dummy shipment JSON"

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

        forward = payload.get("forward_shipments", {}) or {}
        names = []
        for _, row in forward.items():
            n = (row or {}).get("customer")
            if isinstance(n, str) and n.strip():
                names.append(n.strip())

        unique_names = sorted({n for n in names})
        created = 0
        existing = 0

        with transaction.atomic(using="shopcore"):
            for name in unique_names:
                user = User.objects.using("shopcore").filter(name__iexact=name).first()
                if user:
                    existing += 1
                    continue

                User.objects.using("shopcore").create(
                    name=name,
                    email=None,
                    premium_status=False,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Seeded ShopCore users. created={created} existing={existing}"))

    def _email_for_name(self, name: str) -> str:
        local = (name or "").strip().lower()
        local = re.sub(r"[^a-z0-9]+", ".", local)
        local = re.sub(r"\.+", ".", local).strip(".")
        if not local:
            local = "user"
        return f"{local}@example.com"
