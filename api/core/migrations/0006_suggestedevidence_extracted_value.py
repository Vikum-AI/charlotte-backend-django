from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_suggestedsubrule"),
    ]

    operations = [
        migrations.AddField(
            model_name="suggestedevidence",
            name="extracted_value",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
