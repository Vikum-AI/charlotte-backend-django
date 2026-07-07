import json
from dataclasses import dataclass

from api.core.utils.evidence.case_scope import get_attached_evidence_ids
from api.core.utils.evidence.queries import get_evidence_by_ids

RESOLVED_STATUSES = frozenset({'MATCHED', 'PROVISIONAL'})


@dataclass
class AttachedEvidence:
    evidence_id: str
    target_field: str
    value: object
    evidence_type: str
    payload: dict
    resolved_status: str


def get_attached_evidence_with_values(case_id: str) -> list[AttachedEvidence]:
    attached_ids = get_attached_evidence_ids(case_id)
    if not attached_ids:
        return []

    evidence_rows = get_evidence_by_ids(list(attached_ids))
    attached = []

    for row in evidence_rows:
        if row.get('resolved_status') not in RESOLVED_STATUSES:
            continue

        payload = _normalize_payload(row.get('payload'))
        evidence_type = row.get('evidence_type') or ''
        target_field, value = _derive_target_field_and_value(evidence_type, payload)

        attached.append(
            AttachedEvidence(
                evidence_id=row['evidence_id'],
                target_field=target_field,
                value=value,
                evidence_type=evidence_type,
                payload=payload,
                resolved_status=row.get('resolved_status') or '',
            ),
        )

    return attached


def _normalize_payload(payload) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    return {}


def _derive_target_field_and_value(evidence_type: str, payload: dict) -> tuple[str, object]:
    if evidence_type == 'kyc_status':
        return 'customer.kyc_status', payload.get('kyc_status_value')

    if evidence_type == 'custom':
        return payload.get('field_path', ''), payload.get('extracted_value')

    if evidence_type == 'approval':
        return 'approval', payload

    return evidence_type, payload
