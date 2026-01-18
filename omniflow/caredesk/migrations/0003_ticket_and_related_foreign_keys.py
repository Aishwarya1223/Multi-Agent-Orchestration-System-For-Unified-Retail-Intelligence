from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("caredesk", "0002_ticketattachment"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="ticket",
                    old_name="user_id",
                    new_name="user",
                ),
                migrations.AlterField(
                    model_name="ticket",
                    name="user",
                    field=models.ForeignKey(
                        db_column="user_id",
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="caredesk_tickets",
                        to="shopcore.user",
                    ),
                ),
                migrations.RenameField(
                    model_name="ticketmessage",
                    old_name="ticket_id",
                    new_name="ticket",
                ),
                migrations.AlterField(
                    model_name="ticketmessage",
                    name="ticket",
                    field=models.ForeignKey(
                        db_column="ticket_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="caredesk.ticket",
                    ),
                ),
                migrations.RenameField(
                    model_name="satisfactionsurvey",
                    old_name="ticket_id",
                    new_name="ticket",
                ),
                migrations.AlterField(
                    model_name="satisfactionsurvey",
                    name="ticket",
                    field=models.ForeignKey(
                        db_column="ticket_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="surveys",
                        to="caredesk.ticket",
                    ),
                ),
                migrations.RenameField(
                    model_name="ticketattachment",
                    old_name="ticket_id",
                    new_name="ticket",
                ),
                migrations.AlterField(
                    model_name="ticketattachment",
                    name="ticket",
                    field=models.ForeignKey(
                        db_column="ticket_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="caredesk.ticket",
                    ),
                ),
            ],
        ),
    ]
