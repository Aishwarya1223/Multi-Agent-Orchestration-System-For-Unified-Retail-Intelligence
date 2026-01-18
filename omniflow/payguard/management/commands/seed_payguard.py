from datetime import date, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from omniflow.payguard.models import Wallet, PaymentMethod, Transaction
from omniflow.shopcore.models import User, Order


class Command(BaseCommand):
    help = "Seed PayGuard wallets, payment methods, and transactions"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=10, help="Number of users to seed wallets for")
        parser.add_argument("--transactions", type=int, default=3, help="Transactions per wallet")

    def handle(self, *args, **options):
        user_limit = int(options.get("users") or 10)
        tx_per_wallet = int(options.get("transactions") or 3)

        users = list(User.objects.using("shopcore").order_by("id").values_list("id", flat=True)[:user_limit])
        if not users:
            self.stdout.write(self.style.WARNING("No ShopCore users found. Seed ShopCore first."))
            return

        providers = ["VISA", "MASTERCARD", "UPI"]
        currencies = ["INR"]

        created_wallets = 0
        created_methods = 0
        created_tx = 0

        with transaction.atomic(using="payguard"):
            for uid in users:
                wallet = Wallet.objects.using("payguard").filter(user_id=int(uid)).first()
                if not wallet:
                    wallet = Wallet.objects.using("payguard").create(
                        user_id=int(uid),
                        balance=Decimal("0.00"),
                        currency=random.choice(currencies),
                    )
                    created_wallets += 1

                if not PaymentMethod.objects.using("payguard").filter(wallet_id=wallet.id).exists():
                    PaymentMethod.objects.using("payguard").create(
                        wallet=wallet,
                        provider=random.choice(providers),
                        expiry_date=date.today() + timedelta(days=365 * 2),
                    )
                    created_methods += 1

                order_ids = list(Order.objects.using("shopcore").filter(user_id=int(uid)).values_list("id", flat=True)[:tx_per_wallet])
                if not order_ids:
                    with transaction.atomic(using="shopcore"):
                        for _ in range(tx_per_wallet):
                            o = Order.objects.using("shopcore").create(
                                user_id=int(uid),
                                product_id=1,
                                order_date=date.today(),
                                status="PAID",
                            )
                            order_ids.append(o.id)

                for i in range(tx_per_wallet):
                    order_id = int(order_ids[i % len(order_ids)])
                    amount = Decimal(str(random.choice([199, 299, 499, 899, 1200, 1800])))
                    tx_type = random.choice(["Debit", "Refund"])
                    if tx_type == "Debit":
                        wallet.balance = (wallet.balance or Decimal("0.00")) + amount
                    else:
                        wallet.balance = (wallet.balance or Decimal("0.00")) - amount

                    Transaction.objects.using("payguard").create(
                        wallet=wallet,
                        order_id=order_id,
                        amount=amount,
                        type=tx_type,
                    )
                    created_tx += 1

                wallet.save(using="payguard")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Seeded PayGuard. wallets_created={created_wallets} methods_created={created_methods} transactions_created={created_tx}"
            )
        )
