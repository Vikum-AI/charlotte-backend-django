from api.core.utils.rule_engine.types import FAIL, PASS, PENDING

PROVISIONAL_CONFIRMATION_DETAIL = (
    "Provisional evidence attached — confirmation required"
)


def result_status_for_evidence(
    evidence_ids: list[str],
    attached_evidence: list,
    *,
    satisfied: bool,
) -> tuple[str, str | None]:
    if not satisfied:
        return FAIL, None

    if not evidence_ids:
        return PASS, None

    status_by_id = {
        item.evidence_id: item.resolved_status
        for item in attached_evidence
    }
    if any(status_by_id.get(evidence_id) == "PROVISIONAL" for evidence_id in evidence_ids):
        return PENDING, PROVISIONAL_CONFIRMATION_DETAIL

    return PASS, None
