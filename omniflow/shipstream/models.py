from django.db import models
from decimal import Decimal


class Warehouse(models.Model):
    location = models.CharField(max_length=100)
    manager_name = models.CharField(max_length=100)

    def __str__(self):
        return self.location


class Shipment(models.Model):
    order = models.ForeignKey(
        "shopcore.Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="shipments",
        db_constraint=False,
    )
    tracking_number = models.CharField(max_length=50, unique=True,default='')
    estimated_arrival = models.DateField(null=True, blank=True,default=None)
    shipment_date = models.DateField(null=True, blank=True,default=None)
    customer_name = models.CharField(max_length=100, blank=True,default='')
    status = models.CharField(max_length=50, blank=True,default='')
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    notes = models.TextField(blank=True,default='')

    def __str__(self):
        return f"{self.tracking_number} ({self.status})"


class ReturnRequest(models.Model):
    return_id = models.CharField(max_length=50, unique=True, default="")
    tracking_number = models.CharField(max_length=50, default="")
    user_email = models.EmailField(null=True, blank=True)
    image_blob = models.BinaryField(null=True, blank=True)
    image_mime_type = models.CharField(max_length=100, default="")
    status = models.CharField(max_length=50, default="Initiated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.return_id


class TrackingEvent(models.Model):
    shipment_id = models.IntegerField()
    warehouse_id = models.IntegerField()
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

