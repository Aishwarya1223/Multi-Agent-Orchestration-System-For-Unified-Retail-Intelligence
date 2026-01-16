from django.db import models

# Create your models here.
from django.db import models


class Ticket(models.Model):
    user_id = models.IntegerField()            # reference to shopcore.User.id
    reference_id = models.CharField(max_length=50)  # OrderID or TransactionID
    issue_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30)

    def __str__(self):
        return f"Ticket {self.id}"


class TicketMessage(models.Model):
    ticket_id = models.IntegerField()          # reference to Ticket.id
    sender = models.CharField(max_length=10)   # User / Agent
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sender


class SatisfactionSurvey(models.Model):
    ticket_id = models.IntegerField()           # reference to Ticket.id
    rating = models.IntegerField()
    comments = models.TextField(blank=True)

    def __str__(self):
        return f"Rating {self.rating}"


class TicketAttachment(models.Model):
    ticket_id = models.IntegerField()
    kind = models.CharField(max_length=30, default="item_photo")
    image_data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.id} (Ticket {self.ticket_id})"
