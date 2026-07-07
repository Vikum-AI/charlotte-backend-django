from dataclasses import asdict

from api.core.utils.evidence import get_attached_evidence_with_values
from api.core.utils.rule_engine.confirmation import PROVISIONAL_CONFIRMATION_DETAIL
from api.core.utils.rule_engine.tree import resolve_tree
from api.core.utils.rule_engine.types import FAIL, PASS, PENDING, RuleEvaluationResult


def evaluate_rule(case_rule) -> RuleEvaluationResult:
    transaction_id = case_rule.case.transaction_id
    attached_evidence = get_attached_evidence_with_values(case_rule.case_id)

    status, leaf_results = resolve_tree(
        case_rule.definition,
        case_rule.case_id,
        transaction_id,
        attached_evidence,
    )

    reason = _build_reason(status, leaf_results)
    evidence_used = sorted({evidence_id for leaf in leaf_results for evidence_id in leaf.evidence_used})

    return RuleEvaluationResult(
        status=status,
        leaf_results=[asdict(leaf) for leaf in leaf_results],
        reason=reason,
        evidence_used=evidence_used,
    )


def _build_reason(status: str, leaf_results: list) -> str:
    if status == FAIL:
        failing = [leaf for leaf in leaf_results if leaf.status == FAIL]
        return "; ".join(leaf.label for leaf in failing) or "Condition not met"

    if status == PENDING:
        pending = [leaf for leaf in leaf_results if leaf.status == PENDING]
        needs_confirm = any(
            leaf.detail == PROVISIONAL_CONFIRMATION_DETAIL for leaf in pending
        )
        needs_other = any(
            leaf.detail != PROVISIONAL_CONFIRMATION_DETAIL for leaf in pending
        )
        labels = "; ".join(leaf.label for leaf in pending)
        if needs_confirm and not needs_other:
            return f"{labels} — confirmation required"
        if needs_confirm:
            return f"{labels} — awaiting evidence or confirmation"
        return f"{labels} — awaiting evidence"

    return "All conditions satisfied"
