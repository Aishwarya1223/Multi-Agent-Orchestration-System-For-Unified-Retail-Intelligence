from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shipstream", "0005_alter_shipment_order_db_constraint"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="trackingevent",
                    old_name="shipment_id",
                    new_name="shipment",
                ),
                migrations.AlterField(
                    model_name="trackingevent",
                    name="shipment",
                    field=models.ForeignKey(
                        db_column="shipment_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tracking_events",
                        to="shipstream.shipment",
                    ),
                ),
                migrations.RenameField(
                    model_name="trackingevent",
                    old_name="warehouse_id",
                    new_name="warehouse",
                ),
                migrations.AlterField(
                    model_name="trackingevent",
                    name="warehouse",
                    field=models.ForeignKey(
                        db_column="warehouse_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tracking_events",
                        to="shipstream.warehouse",
                    ),
                ),
            ],
        ),
    ]
