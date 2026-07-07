from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_caserule_and_evaluation"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuggestedEvidence",
            fields=[
                ("id", models.CharField(max_length=50, primary_key=True, serialize=False)),
                ("label", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "evidence_type",
                    models.CharField(
                        choices=[
                            ("approval", "Approval"),
                            ("kyc_status", "KYC status"),
                            ("custom", "Custom"),
                        ],
                        max_length=20,
                    ),
                ),
                ("file_key", models.CharField(max_length=255)),
                ("file_url", models.URLField()),
                ("applicable_transaction_ids", models.JSONField(default=list)),
                ("field_path", models.CharField(blank=True, max_length=200, null=True)),
                ("suggested_condition", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
