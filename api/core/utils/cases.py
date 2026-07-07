from django.core.exceptions import ObjectDoesNotExist

from api.core.models import Case, CaseRule


def serialize_case_list_item(case: Case) -> dict:
    return {
        "id": case.id,
        "transaction_id": case.transaction_id,
        "status": case.status,
        "assigned_to": case.assigned_to,
        "created_at": case.created_at,
    }


def serialize_case_rule(case_rule: CaseRule) -> dict:
    try:
        evaluation = case_rule.evaluation
    except ObjectDoesNotExist:
        evaluation = None

    return {
        "rule_id": case_rule.rule_id,
        "definition": case_rule.definition,
        "status": getattr(evaluation, "status", None),
        "leaf_results": getattr(evaluation, "leaf_results", []),
        "reason": getattr(evaluation, "reason", ""),
        "evidence_used": getattr(evaluation, "evidence_used", []),
        "is_stale": getattr(evaluation, "is_stale", True),
    }
