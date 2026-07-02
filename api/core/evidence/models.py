from django.db import models


class CaseEvidence(models.Model):
    case_id = models.CharField(max_length=50)
    evidence_id = models.CharField(max_length=50)
    attached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'case_evidence'
        constraints = [
            models.UniqueConstraint(
                fields=['case_id', 'evidence_id'],
                name='uniq_case_evidence',
            ),
        ]
