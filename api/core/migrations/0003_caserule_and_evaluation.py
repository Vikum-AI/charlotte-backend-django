import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_case_and_caseevidence_fk'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rule_id', models.CharField(max_length=100)),
                ('definition', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='core.case')),
            ],
        ),
        migrations.CreateModel(
            name='CaseRuleEvaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PASS', 'Pass'), ('FAIL', 'Fail'), ('PENDING', 'Pending')], default='PENDING', max_length=20)),
                ('leaf_results', models.JSONField(default=list)),
                ('reason', models.TextField(blank=True)),
                ('evidence_used', models.JSONField(default=list)),
                ('computed_at', models.DateTimeField(blank=True, null=True)),
                ('is_stale', models.BooleanField(default=True)),
                ('case_rule', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='evaluation', to='core.caserule')),
            ],
        ),
    ]
