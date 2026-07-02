from django.utils import timezone

from api.core.graph.models.financial import Transaction
from api.core.graph.models.investigation import Evidence
from api.core.utils.evidence.exceptions import EvidenceCreationError
from api.core.utils.evidence.resolvers import (
    MATCHED,
    MISMATCH,
    resolve_approval,
    resolve_custom,
    resolve_kyc_status,
)


def create_approval_evidence(
    evidence_id: str,
    transaction_id: str,
    source_document_id: str,
    source_text: str,
    approver_email: str | None,
    approval_date: str | None,
    confidence: float,
    raw_extraction: dict,
    source_start_offset: int | None = None,
    source_end_offset: int | None = None,
    file_key: str | None = None,
) -> Evidence:
    result = resolve_approval(transaction_id, approver_email, approval_date)
    payload = _build_payload(
        result,
        {
            'approver_email': approver_email,
            'approval_date': approval_date,
        },
    )
    return _create_evidence(
        evidence_id=evidence_id,
        evidence_type='approval',
        transaction_id=transaction_id,
        source_document_id=source_document_id,
        source_text=source_text,
        confidence=confidence,
        raw_extraction=raw_extraction,
        source_start_offset=source_start_offset,
        source_end_offset=source_end_offset,
        file_key=file_key,
        resolved_status=result.status,
        resolution_reason=result.reason,
        payload=payload,
    )


def create_kyc_evidence(
    evidence_id: str,
    customer_id: str,
    transaction_id: str,
    source_document_id: str,
    source_text: str,
    kyc_status_value: str | None,
    verification_date: str | None,
    confidence: float,
    raw_extraction: dict,
    source_start_offset: int | None = None,
    source_end_offset: int | None = None,
    file_key: str | None = None,
) -> Evidence:
    result = resolve_kyc_status(customer_id, kyc_status_value, verification_date)
    payload = _build_payload(
        result,
        {
            'kyc_status_value': kyc_status_value,
            'verification_date': verification_date,
            'customer_id': customer_id,
        },
    )
    return _create_evidence(
        evidence_id=evidence_id,
        evidence_type='kyc_status',
        transaction_id=transaction_id,
        source_document_id=source_document_id,
        source_text=source_text,
        confidence=confidence,
        raw_extraction=raw_extraction,
        source_start_offset=source_start_offset,
        source_end_offset=source_end_offset,
        file_key=file_key,
        resolved_status=result.status,
        resolution_reason=result.reason,
        payload=payload,
    )


def create_custom_evidence(
    evidence_id: str,
    transaction_id: str,
    field_path: str,
    source_document_id: str,
    source_text: str,
    extracted_value: str,
    confidence: float,
    raw_extraction: dict,
    source_start_offset: int | None = None,
    source_end_offset: int | None = None,
    file_key: str | None = None,
    customer_id: str | None = None,
) -> Evidence:
    result = resolve_custom(field_path, extracted_value, transaction_id, customer_id)
    payload = _build_payload(
        result,
        {
            'field_path': field_path,
            'extracted_value': extracted_value,
        },
    )
    return _create_evidence(
        evidence_id=evidence_id,
        evidence_type='custom',
        transaction_id=transaction_id,
        source_document_id=source_document_id,
        source_text=source_text,
        confidence=confidence,
        raw_extraction=raw_extraction,
        source_start_offset=source_start_offset,
        source_end_offset=source_end_offset,
        file_key=file_key,
        resolved_status=result.status,
        resolution_reason=result.reason,
        payload=payload,
    )


def _build_payload(result, raw_fields: dict) -> dict:
    if result.status in (MATCHED, MISMATCH) and result.resolved_payload is not None:
        return result.resolved_payload
    return {key: value for key, value in raw_fields.items() if value is not None}


def _create_evidence(
    *,
    evidence_id: str,
    evidence_type: str,
    transaction_id: str,
    source_document_id: str,
    source_text: str,
    confidence: float,
    raw_extraction: dict,
    resolved_status: str,
    resolution_reason: str | None,
    payload: dict,
    source_start_offset: int | None = None,
    source_end_offset: int | None = None,
    file_key: str | None = None,
) -> Evidence:
    try:
        transaction = Transaction.nodes.get(transaction_id=transaction_id)
    except Transaction.DoesNotExist as exc:
        raise EvidenceCreationError(
            f"Transaction '{transaction_id}' not found",
        ) from exc

    try:
        evidence = Evidence(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            extracted_at=timezone.now(),
            confidence=confidence,
            source_document_id=source_document_id,
            file_key=file_key,
            source_text=source_text,
            source_start_offset=source_start_offset,
            source_end_offset=source_end_offset,
            raw_extraction=raw_extraction,
            resolved_status=resolved_status,
            resolution_reason=resolution_reason,
            payload=payload,
        )
        evidence.save()
        evidence.supports.connect(transaction)
        return evidence
    except Exception as exc:
        raise EvidenceCreationError(
            f"Failed to create evidence '{evidence_id}': {exc}",
        ) from exc
