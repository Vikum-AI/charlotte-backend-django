from api.core.models import Case, CaseEvidence, SuggestedEvidence
from api.core.utils.evidence.queries import get_evidence_by_ids


def is_suggested_evidence_applicable(
    suggested: SuggestedEvidence,
    case: Case,
) -> bool:
    transaction_ids = suggested.applicable_transaction_ids or []
    return not transaction_ids or case.transaction_id in transaction_ids


def suggested_evidence_metadata(suggested: SuggestedEvidence) -> dict:
    metadata = {
        "file_url": suggested.file_url,
        "file_key": suggested.file_key,
        "evidence_type_hint": suggested.evidence_type,
        "field_path": suggested.field_path,
        "extracted_value": suggested.extracted_value,
        "suggested_evidence_id": suggested.id,
    }
    return {key: value for key, value in metadata.items() if value not in (None, "")}


def already_added_suggested_evidence_ids(
    case: Case,
    suggested_items: list[SuggestedEvidence],
) -> set[str]:
    attached_evidence_ids = list(
        CaseEvidence.objects.filter(case=case).values_list("evidence_id", flat=True)
    )
    if not attached_evidence_ids:
        return set()

    suggested_by_file_key = {
        item.file_key: item.id
        for item in suggested_items
        if item.file_key
    }
    suggested_by_file_url = {
        item.file_url: item.id
        for item in suggested_items
        if item.file_url
    }

    try:
        evidence_rows = get_evidence_by_ids(attached_evidence_ids)
    except Exception:
        return set()

    already_added = set()
    for row in evidence_rows:
        file_key = row.get("file_key")
        source_document_id = row.get("source_document_id")
        if file_key in suggested_by_file_key:
            already_added.add(suggested_by_file_key[file_key])
        if source_document_id in suggested_by_file_url:
            already_added.add(suggested_by_file_url[source_document_id])
    return already_added
