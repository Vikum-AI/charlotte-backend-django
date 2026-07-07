import re
from datetime import datetime, timedelta, timezone

from api.core.utils.rule_engine.confirmation import result_status_for_evidence
from api.core.utils.rule_engine.evidence_filters import evidence_matches_filter
from api.core.utils.rule_engine.field_resolver import (
    aggregate_related,
    count_all_evidence_of_type,
    find_matching_evidence,
    is_evidence_only_field,
    resolve_field,
    resolve_field_for_case,
)
from api.core.utils.rule_engine.labels import make_label
from api.core.utils.rule_engine.operators import apply_op
from api.core.utils.rule_engine.types import ConditionResult, FAIL, PASS, PENDING


def resolve_comparison(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id
    label = make_label(cond)
    real_value = resolve_field_for_case(cond["field"], transaction_id)

    if real_value is not None:
        status = PASS if apply_op(real_value, cond["op"], cond["value"]) else FAIL
        return ConditionResult(status=status, label=label)

    match = find_matching_evidence(cond["field"], attached_evidence)
    if match is None:
        return ConditionResult(status=PENDING, label=label)

    op_satisfied = apply_op(match.value, cond["op"], cond["value"])
    status, detail = result_status_for_evidence(
        [match.evidence_id],
        attached_evidence,
        satisfied=op_satisfied,
    )
    return ConditionResult(
        status=status,
        label=label,
        evidence_used=[match.evidence_id],
        detail=detail,
    )


def resolve_presence(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id
    label = make_label(cond)
    real_value = resolve_field_for_case(cond["field"], transaction_id)

    if real_value is not None:
        return ConditionResult(status=PASS, label=label)

    match = find_matching_evidence(cond["field"], attached_evidence)
    if match is None:
        return ConditionResult(status=PENDING, label=label)

    status, detail = result_status_for_evidence(
        [match.evidence_id],
        attached_evidence,
        satisfied=True,
    )
    return ConditionResult(
        status=status,
        label=label,
        evidence_used=[match.evidence_id],
        detail=detail,
    )


def resolve_membership(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id
    label = make_label(cond)
    real_value = resolve_field_for_case(cond["field"], transaction_id)
    target = cond["values"]

    if real_value is not None:
        status = PASS if apply_op(real_value, cond["op"], target) else FAIL
        return ConditionResult(status=status, label=label)

    match = find_matching_evidence(cond["field"], attached_evidence)
    if match is None:
        return ConditionResult(status=PENDING, label=label)

    op_satisfied = apply_op(match.value, cond["op"], target)
    status, detail = result_status_for_evidence(
        [match.evidence_id],
        attached_evidence,
        satisfied=op_satisfied,
    )
    return ConditionResult(
        status=status,
        label=label,
        evidence_used=[match.evidence_id],
        detail=detail,
    )


def resolve_string_match(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id
    label = make_label(cond)
    real_value = resolve_field_for_case(cond["field"], transaction_id)

    if real_value is not None:
        status = PASS if apply_op(real_value, cond["op"], cond["value"]) else FAIL
        return ConditionResult(status=status, label=label)

    match = find_matching_evidence(cond["field"], attached_evidence)
    if match is None:
        return ConditionResult(status=PENDING, label=label)

    op_satisfied = apply_op(match.value, cond["op"], cond["value"])
    status, detail = result_status_for_evidence(
        [match.evidence_id],
        attached_evidence,
        satisfied=op_satisfied,
    )
    return ConditionResult(
        status=status,
        label=label,
        evidence_used=[match.evidence_id],
        detail=detail,
    )


def _resolve_cross_field_value(
    field_path: str,
    transaction_id: str,
    attached_evidence: list,
):
    if is_evidence_only_field(field_path):
        match = find_matching_evidence(field_path, attached_evidence)
        return match.value if match else None
    return resolve_field(field_path, transaction_id)


def resolve_cross_field(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id

    label = make_label(cond)
    value_a = _resolve_cross_field_value(cond["field_a"], transaction_id, attached_evidence)
    value_b = _resolve_cross_field_value(cond["field_b"], transaction_id, attached_evidence)

    if value_a is None or value_b is None:
        return ConditionResult(
            status=PENDING,
            label=label,
            detail="one or both fields not yet resolvable",
        )

    status = PASS if apply_op(value_a, cond["op"], value_b) else FAIL
    return ConditionResult(status=status, label=label)


def resolve_temporal(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id
    label = make_label(cond)
    real_value = resolve_field_for_case(cond["field"], transaction_id)
    evidence_used = []

    if real_value is None:
        match = find_matching_evidence(cond["field"], attached_evidence)
        if match is None:
            return ConditionResult(status=PENDING, label=label)
        real_value = match.value
        evidence_used = [match.evidence_id]

    field_dt = real_value if isinstance(real_value, datetime) else datetime.fromisoformat(str(real_value))
    if field_dt.tzinfo is None:
        field_dt = field_dt.replace(tzinfo=timezone.utc)

    if cond["op"] == "within_last":
        pattern = re.match(r"(\d+)([dhm])", cond["value"])
        amount, unit = int(pattern.group(1)), pattern.group(2)
        delta = {
            "d": timedelta(days=amount),
            "h": timedelta(hours=amount),
            "m": timedelta(minutes=amount),
        }[unit]
        op_satisfied = datetime.now(timezone.utc) - field_dt <= delta
    else:
        target_dt = datetime.fromisoformat(cond["value"]).replace(tzinfo=timezone.utc)
        op_satisfied = apply_op(field_dt, cond["op"], target_dt)

    status, detail = result_status_for_evidence(
        evidence_used,
        attached_evidence,
        satisfied=op_satisfied,
    )
    return ConditionResult(
        status=status,
        label=label,
        evidence_used=evidence_used,
        detail=detail,
    )


def resolve_count(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    label = make_label(cond)
    filter_spec = cond.get("filter")
    relationship = cond["relationship"]
    threshold = cond["value"]
    op = cond.get("op", "gte")

    total_existing = count_all_evidence_of_type(
        case_id,
        transaction_id,
        relationship,
        filter_spec,
    )
    confirmed = [
        evidence for evidence in attached_evidence
        if evidence.evidence_type == relationship and _matches_filter(evidence, filter_spec)
    ]
    confirmed_count = len(confirmed)

    if apply_op(confirmed_count, op, threshold):
        evidence_ids = [evidence.evidence_id for evidence in confirmed]
        status, detail = result_status_for_evidence(
            evidence_ids,
            attached_evidence,
            satisfied=True,
        )
        count_detail = f"{confirmed_count}/{threshold} confirmed"
        return ConditionResult(
            status=status,
            label=label,
            evidence_used=evidence_ids,
            detail=detail or count_detail,
        )

    if total_existing < threshold:
        return ConditionResult(
            status=FAIL,
            label=label,
            detail=f"only {total_existing} exist, need {threshold}",
        )

    return ConditionResult(
        status=PENDING,
        label=label,
        evidence_used=[evidence.evidence_id for evidence in confirmed],
        detail=f"{confirmed_count}/{threshold} confirmed",
    )


def resolve_aggregate(cond, case_id, transaction_id, attached_evidence) -> ConditionResult:
    del case_id, attached_evidence

    label = make_label(cond)
    result = aggregate_related(
        transaction_id,
        cond["relationship"],
        cond["field"],
        cond["fn"],
        window=cond.get("window"),
        filter_spec=cond.get("filter"),
    )

    if result is None:
        return ConditionResult(status=PENDING, label=label)

    status = PASS if apply_op(result, cond["op"], cond["value"]) else FAIL
    return ConditionResult(status=status, label=label, detail=f"computed: {result}")


def _matches_filter(evidence, filter_spec: dict | None) -> bool:
    if not filter_spec:
        return True

    return evidence_matches_filter(evidence, filter_spec)


CONDITION_RESOLVERS = {
    "comparison": resolve_comparison,
    "presence": resolve_presence,
    "membership": resolve_membership,
    "string_match": resolve_string_match,
    "cross_field": resolve_cross_field,
    "temporal": resolve_temporal,
    "count": resolve_count,
    "aggregate": resolve_aggregate,
}
