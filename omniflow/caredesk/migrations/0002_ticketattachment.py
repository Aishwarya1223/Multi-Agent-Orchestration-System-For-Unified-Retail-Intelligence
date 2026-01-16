from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("caredesk", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TicketAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ticket_id", models.IntegerField()),
                ("kind", models.CharField(default="item_photo", max_length=30)),
                ("image_data", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
