from payguard.services import (
    get_wallet_by_user_id,
    get_transactions_for_order,
)


def payguard_agent(user_id: int, order_id: int):
    """
    Fetches wallet and payment/refund history for an order.
    """

    wallet = get_wallet_by_user_id(user_id)
    if not wallet:
        return None

    transactions = get_transactions_for_order(order_id)

    return {
        "wallet_id": wallet.id,
        "balance": str(wallet.balance),
        "currency": wallet.currency,
        "transactions": [
            {
                "amount": str(tx.amount),
                "type": tx.type,
                "timestamp": str(tx.timestamp),
            }
            for tx in transactions
        ],
    }