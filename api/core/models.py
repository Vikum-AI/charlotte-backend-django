from django.core.exceptions import ValidationError
from django.db import models
from api.core.graph import (
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
from api.core.utils.rule_engine.validation import (
    ConditionValidationError,
    validate_leaf_condition,
)


class Status(models.TextChoices):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


class Tier(models.TextChoices):
    TRANSACTION = "transaction", "Transaction"
    ACCOUNT = "account", "Account"
    CUSTOMER = "customer", "Customer"


class ConditionType(models.TextChoices):
    COMPARISON = "comparison", "Comparison"
    PRESENCE = "presence", "Presence"
    MEMBERSHIP = "membership", "Membership"
    STRING_MATCH = "string_match", "String match"
    CROSS_FIELD = "cross_field", "Cross field"
    TEMPORAL = "temporal", "Temporal"
    COUNT = "count", "Count"
    AGGREGATE = "aggregate", "Aggregate"


class EvidenceType(models.TextChoices):
    APPROVAL = "approval", "Approval"
    KYC_STATUS = "kyc_status", "KYC status"
    CUSTOM = "custom", "Custom"


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


class CaseRule(models.Model):
    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="rules")
    rule_id = models.CharField(max_length=100)
    definition = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class CaseRuleEvaluation(models.Model):
    case_rule = models.OneToOneField(
        CaseRule, on_delete=models.CASCADE, related_name="evaluation")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    leaf_results = models.JSONField(default=list)
    reason = models.TextField(blank=True)
    evidence_used = models.JSONField(default=list)
    computed_at = models.DateTimeField(null=True, blank=True)
    is_stale = models.BooleanField(default=True)


class SuggestedSubRule(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tier = models.CharField(max_length=20, choices=Tier.choices)
    condition_type = models.CharField(
        max_length=20, choices=ConditionType.choices)
    condition_fragment = models.JSONField()
    applicable_transaction_ids = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        try:
            validate_leaf_condition(
                self.condition_fragment,
                expected_type=self.condition_type,
            )
        except ConditionValidationError as exc:
            raise ValidationError({"condition_fragment": str(exc)}) from exc

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SuggestedEvidence(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    evidence_type = models.CharField(
        max_length=20, choices=EvidenceType.choices)
    file_key = models.CharField(max_length=255)
    file_url = models.URLField()
    applicable_transaction_ids = models.JSONField(default=list)
    field_path = models.CharField(max_length=200, blank=True, null=True)
    extracted_value = models.CharField(max_length=200, blank=True, null=True)
    suggested_condition = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
