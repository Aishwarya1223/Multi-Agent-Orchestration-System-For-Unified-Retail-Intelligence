from caredesk.services import (
    get_latest_ticket_for_user,
    get_messages_for_ticket,
)


def caredesk_agent(user_id: int):
    """
    Fetches latest support ticket and messages for a user.
    """

    ticket = get_latest_ticket_for_user(user_id)
    if not ticket:
        return None

    messages = get_messages_for_ticket(ticket.id)

    return {
        "ticket_id": ticket.id,
        "issue_type": ticket.issue_type,
        "status": ticket.status,
        "created_at": str(ticket.created_at),
        "messages": [
            {
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": str(msg.timestamp),
            }
            for msg in messages
        ],
    }
