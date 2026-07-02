from django.db import models
from api.core.graph import (  # noqa: F401
    Account,
    AMLCheck,
    Approval,
    Case as DeprecatedCase,
    Country,
    Customer,
    CustomerBehaviourProfile,
    Employee,
    Evidence,
    RiskSignal,
    Rule,
    RuleEvaluation,
    Transaction,
)


class Case(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    # references Neo4j Transaction.transaction_id
    transaction_id = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default="open")

    assigned_to = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CaseEvidence(models.Model):
    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="case_evidence")

    evidence_id = models.CharField(max_length=50)
    attached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["case", "evidence_id"], name="uniq_case_evidence"),
        ]


class SuggestedSubRules(models.Model):
    ...


class SuggestedEvidence(models.Model):
    ...
