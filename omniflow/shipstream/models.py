from django.db import models

# Create your models here.
from django.db import models
from decimal import Decimal


class Warehouse(models.Model):
    location = models.CharField(max_length=100)
    manager_name = models.CharField(max_length=100)

    def __str__(self):
        return self.location


class Shipment(models.Model):
    order_id = models.IntegerField(null=True, blank=True)          # reference to shopcore.Order.id
    tracking_number = models.CharField(max_length=50, unique=True)
    estimated_arrival = models.DateField(null=True, blank=True)
    shipment_date = models.DateField(null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.tracking_number


class TrackingEvent(models.Model):
    shipment_id = models.IntegerField()       # reference to Shipment.id
    warehouse_id = models.IntegerField()      # reference to Warehouse.id
    timestamp = models.DateTimeField()
    status_update = models.CharField(max_length=100)

    def __str__(self):
        return self.status_update


class ReverseShipment(models.Model):
    reverse_number = models.CharField(max_length=50, unique=True)
    original_shipment = models.ForeignKey(
        Shipment,
        to_field="tracking_number",
        db_column="original_awb",
        on_delete=models.CASCADE,
        related_name="reverse_shipments",
    )
    return_date = models.DateField()
    reason = models.CharField(max_length=200)
    refund_status = models.CharField(max_length=50)

    def __str__(self):
        return self.reverse_number


class NdrEvent(models.Model):
    ndr_number = models.CharField(max_length=50, unique=True)
    original_shipment = models.ForeignKey(
        Shipment,
        to_field="tracking_number",
        db_column="original_awb",
        on_delete=models.CASCADE,
        related_name="ndr_events",
    )
    ndr_date = models.DateField()
    issue = models.CharField(max_length=200)
    attempts = models.IntegerField(default=1)
    final_outcome = models.CharField(max_length=50)

    def __str__(self):
        return self.ndr_number


class ExchangeShipment(models.Model):
    exchange_number = models.CharField(max_length=50, unique=True)
    original_shipment = models.ForeignKey(
        Shipment,
        to_field="tracking_number",
        db_column="original_awb",
        on_delete=models.CASCADE,
        related_name="exchange_shipments",
    )
    exchange_date = models.DateField()
    new_item = models.CharField(max_length=200)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.exchange_number

