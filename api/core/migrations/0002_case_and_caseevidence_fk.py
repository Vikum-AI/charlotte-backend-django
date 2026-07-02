import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Case',
            fields=[
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('transaction_id', models.CharField(max_length=50)),
                ('status', models.CharField(default='open', max_length=20)),
                ('assigned_to', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.RemoveConstraint(
            model_name='caseevidence',
            name='uniq_case_evidence',
        ),
        migrations.AlterModelTable(
            name='caseevidence',
            table=None,
        ),
        migrations.RemoveField(
            model_name='caseevidence',
            name='case_id',
        ),
        migrations.AddField(
            model_name='caseevidence',
            name='case',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='case_evidence',
                to='core.case',
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='caseevidence',
            constraint=models.UniqueConstraint(
                fields=('case', 'evidence_id'),
                name='uniq_case_evidence',
            ),
        ),
    ]
