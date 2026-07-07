from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_suggestedevidence"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuggestedSubRule",
            fields=[
                ("id", models.CharField(max_length=50, primary_key=True, serialize=False)),
                ("label", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("transaction", "Transaction"),
                            ("account", "Account"),
                            ("customer", "Customer"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "condition_type",
                    models.CharField(
                        choices=[
                            ("comparison", "Comparison"),
                            ("presence", "Presence"),
                            ("membership", "Membership"),
                            ("string_match", "String match"),
                            ("cross_field", "Cross field"),
                            ("temporal", "Temporal"),
                            ("count", "Count"),
                            ("aggregate", "Aggregate"),
                        ],
                        max_length=20,
                    ),
                ),
                ("condition_fragment", models.JSONField()),
                ("applicable_transaction_ids", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
