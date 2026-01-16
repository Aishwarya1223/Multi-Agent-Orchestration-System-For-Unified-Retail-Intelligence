from .models import Ticket, TicketMessage


def get_latest_ticket_for_user(user_id: int):
    return (
        Ticket.objects
        .filter(user_id=user_id)
        .order_by("-created_at")
        .first()
    )


def get_messages_for_ticket(ticket_id: int):
    return (
        TicketMessage.objects
        .filter(ticket_id=ticket_id)
        .order_by("timestamp")
    )