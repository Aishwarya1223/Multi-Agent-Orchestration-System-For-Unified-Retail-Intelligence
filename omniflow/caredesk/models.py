from django.db import models

# Create your models here.
from django.db import models


class Ticket(models.Model):
    user = models.ForeignKey(
        "shopcore.User",
        on_delete=models.DO_NOTHING,
        related_name="caredesk_tickets",
        db_column="user_id",
        db_constraint=False,
    )
    reference_id = models.CharField(max_length=50)  # OrderID or TransactionID
    issue_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30)

    def __str__(self):
        return f"Ticket {self.id}"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
        db_column="ticket_id",
    )
    sender = models.CharField(max_length=10)   # User / Agent
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sender


class SatisfactionSurvey(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="surveys",
        db_column="ticket_id",
    )
    rating = models.IntegerField()
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"Rating {self.rating}"


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
        db_column="ticket_id",
    )
    kind = models.CharField(max_length=30, default="item_photo")
    image_data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.id} (Ticket {self.ticket_id})"
