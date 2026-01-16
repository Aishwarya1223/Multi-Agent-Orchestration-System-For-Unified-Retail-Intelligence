from .models import Wallet, Transaction


def get_wallet_by_user_id(user_id: int):
    return Wallet.objects.filter(user_id=user_id).first()


def get_transactions_for_order(order_id: int):
    return Transaction.objects.filter(order_id=order_id).order_by("-timestamp")