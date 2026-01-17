from django.core.management.base import BaseCommand
from django.db import transaction
from omniflow.shipstream.models import Shipment
from omniflow.shopcore.models import User, Order

class Command(BaseCommand):
    help = "Link shipments to orders using customer ownership"

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        with transaction.atomic():
            for shipment in Shipment.objects.using("shipstream").all():

                if shipment.order_id:
                    try:
                        Order.objects.using("shopcore").get(id=shipment.order_id)
                        skipped += 1
                        continue
                    except Order.DoesNotExist:
                        shipment.order = None
                        shipment.save(update_fields=["order"], using="shipstream")

                try:
                    user = User.objects.using("shopcore").get(name=shipment.customer_name)
                except User.DoesNotExist:
                    skipped += 1
                    continue

                order = (
                    Order.objects.using("shopcore")
                    .filter(user=user)
                    .order_by("-id")
                    .first()
                )

                if not order:
                    skipped += 1
                    continue

                shipment.order = order
                shipment.save(update_fields=["order"], using="shipstream")
                updated += 1

