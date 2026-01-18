from django.db import models


class Wallet(models.Model):
    
    user = models.ForeignKey(
        "shopcore.User",
        on_delete=models.DO_NOTHING,
        related_name="payguard_wallets",
        db_column="user_id",
        db_constraint=False,
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)

    def __str__(self):
        return f"Wallet {self.id} (User {self.user_id})"


class PaymentMethod(models.Model):
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="payment_methods",
        db_column="wallet_id",
    )
    provider = models.CharField(max_length=50)
    expiry_date = models.DateField()

    def __str__(self):
        return self.provider


class Transaction(models.Model):
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        db_column="wallet_id",
    )
    order = models.ForeignKey(
        "shopcore.Order",
        on_delete=models.DO_NOTHING,
        related_name="payguard_transactions",
        db_column="order_id",
        db_constraint=False,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.amount}"
