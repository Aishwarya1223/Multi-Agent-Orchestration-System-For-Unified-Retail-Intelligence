from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payguard", "0002_wallet_foreign_keys"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="wallet",
                    old_name="user_id",
                    new_name="user",
                ),
                migrations.AlterField(
                    model_name="wallet",
                    name="user",
                    field=models.ForeignKey(
                        db_column="user_id",
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="payguard_wallets",
                        to="shopcore.user",
                    ),
                ),
                migrations.RenameField(
                    model_name="transaction",
                    old_name="order_id",
                    new_name="order",
                ),
                migrations.AlterField(
                    model_name="transaction",
                    name="order",
                    field=models.ForeignKey(
                        db_column="order_id",
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="payguard_transactions",
                        to="shopcore.order",
                    ),
                ),
            ],
        ),
    ]
