from django.http import Http404
from neomodel import db

EVIDENCE_FIELDS = (
    'evidence_id',
    'case_id',
    'evidence_type',
    'resolved_status',
    'resolution_reason',
    'source_text',
    'payload',
    'confidence',
    'source_document_id',
    'file_key',
    'source_start_offset',
    'source_end_offset',
    'extracted_at',
    'raw_extraction',
)

EVIDENCE_FOR_TRANSACTION_QUERY = f"""
MATCH (e:Evidence)-[:SUPPORTS]->(t:Transaction {{transaction_id: $transaction_id}})
RETURN {', '.join(f'e.{field} AS {field}' for field in EVIDENCE_FIELDS)}
ORDER BY e.extracted_at DESC
"""

EVIDENCE_FOR_CASE_QUERY = f"""
MATCH (e:Evidence {{case_id: $case_id}})
RETURN {', '.join(f'e.{field} AS {field}' for field in EVIDENCE_FIELDS)}
ORDER BY e.extracted_at DESC
"""

EVIDENCE_BY_ID_QUERY = f"""
MATCH (e:Evidence {{evidence_id: $evidence_id}})
RETURN {', '.join(f'e.{field} AS {field}' for field in EVIDENCE_FIELDS)}
"""


EVIDENCE_BY_IDS_QUERY = f"""
MATCH (e:Evidence)
WHERE e.evidence_id IN $evidence_ids
RETURN {', '.join(f'e.{field} AS {field}' for field in EVIDENCE_FIELDS)}
"""


def get_evidence_for_transaction(transaction_id: str) -> list[dict]:
    results, _ = db.cypher_query(
        EVIDENCE_FOR_TRANSACTION_QUERY,
        {'transaction_id': transaction_id},
    )
    return [_row_to_dict(row) for row in results]


def get_evidence_for_case(case_id: str) -> list[dict]:
    results, _ = db.cypher_query(
        EVIDENCE_FOR_CASE_QUERY,
        {'case_id': case_id},
    )
    return [_row_to_dict(row) for row in results]


def get_evidence_by_id(evidence_id: str) -> dict | None:
    results, _ = db.cypher_query(
        EVIDENCE_BY_ID_QUERY,
        {'evidence_id': evidence_id},
    )
    if not results:
        return None
    return _row_to_dict(results[0])


def get_evidence_by_ids(evidence_ids: list[str]) -> list[dict]:
    if not evidence_ids:
        return []

    results, _ = db.cypher_query(
        EVIDENCE_BY_IDS_QUERY,
        {'evidence_ids': evidence_ids},
    )
    return [_row_to_dict(row) for row in results]


def get_existing_evidence_or_404(evidence_id: str) -> dict:
    try:
        evidence = get_evidence_by_id(evidence_id)
    except Exception as exc:
        raise Http404(f"Evidence '{evidence_id}' not found") from exc
    if evidence is None:
        raise Http404(f"Evidence '{evidence_id}' not found")
    return evidence


def _row_to_dict(row) -> dict:
    return {field: row[index] for index, field in enumerate(EVIDENCE_FIELDS)}
