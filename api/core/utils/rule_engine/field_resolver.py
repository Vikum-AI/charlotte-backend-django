import json

from neomodel import db

from api.core.utils.evidence.resolvers import resolve_field_path
from api.core.utils.rule_engine.evidence_filters import payload_matches_filter

EVIDENCE_TYPES = frozenset({"approval", "kyc_status", "custom"})
EVIDENCE_ONLY_FIELD_PATHS = frozenset({
    "customer.kyc_status",
    "transaction.destination_country",
})
EVIDENCE_FILTER_KEYS = frozenset({"role", "approver_email"})
AGGREGATE_FNS = frozenset({"sum", "avg", "count", "min", "max"})
AGGREGATE_RELATIONSHIPS = frozenset({"approvals", "transactions"})
AGGREGATE_FIELDS = frozenset({"amount"})


def resolve_field(field_path: str, transaction_id: str):
    return resolve_field_path(field_path, transaction_id=transaction_id)


def is_evidence_only_field(field_path: str) -> bool:
    return field_path in EVIDENCE_ONLY_FIELD_PATHS


def resolve_field_for_case(field_path: str, transaction_id: str):
    if is_evidence_only_field(field_path):
        return None
    return resolve_field(field_path, transaction_id)


def find_matching_evidence(field_path: str, attached_evidence: list):
    for evidence in attached_evidence:
        if evidence.target_field == field_path:
            return evidence
    return None


def count_all_evidence_of_type(
    case_id: str,
    transaction_id: str,
    relationship: str,
    filter_spec: dict | None,
) -> int:
    if relationship not in EVIDENCE_TYPES:
        raise ValueError(f"Unknown evidence type: '{relationship}'")

    query = """
    MATCH (e:Evidence)-[:SUPPORTS]->(t:Transaction {transaction_id: $transaction_id})
    WHERE e.case_id = $case_id AND e.evidence_type = $evidence_type
    RETURN e.payload AS payload
    """

    results, _ = db.cypher_query(
        query,
        {
            "case_id": case_id,
            "transaction_id": transaction_id,
            "evidence_type": relationship,
        },
    )

    if not filter_spec:
        return len(results)

    allowlisted = {
        key: value
        for key, value in filter_spec.items()
        if key in EVIDENCE_FILTER_KEYS
    }

    if not allowlisted:
        return len(results)

    matched = 0
    for row in results:
        payload = _normalize_payload(row[0])
        if payload_matches_filter(payload, allowlisted):
            matched += 1

    return matched


def _normalize_payload(payload) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    return {}


def aggregate_related(
    transaction_id: str,
    relationship: str,
    field: str,
    fn: str,
    window=None,
    filter_spec=None,
):
    del window, filter_spec

    if relationship not in AGGREGATE_RELATIONSHIPS:
        raise ValueError(f"Unknown aggregate relationship: '{relationship}'")

    if field not in AGGREGATE_FIELDS:
        raise ValueError(f"Unknown aggregate field: '{field}'")

    if fn not in AGGREGATE_FNS:
        raise ValueError(f"Unknown aggregate function: '{fn}'")

    if relationship == "approvals":
        query = """
        MATCH (:Approval)-[:FOR]->(t:Transaction {transaction_id: $transaction_id})
        RETURN count(*) AS value
        """
        results, _ = db.cypher_query(query, {"transaction_id": transaction_id})
        if not results:
            return None
        return results[0][0]

    if relationship == "transactions":
        query = """
        MATCH (source:Account)-[:INITIATES]->(t:Transaction {transaction_id: $transaction_id})
        MATCH (source)-[:INITIATES]->(related:Transaction)
        RETURN related.amount AS amount
        """
        results, _ = db.cypher_query(query, {"transaction_id": transaction_id})
        if not results:
            return None

        amounts = [row[0] for row in results if row[0] is not None]
        if not amounts:
            return None

        if fn == "sum":
            return sum(amounts)
        if fn == "avg":
            return sum(amounts) / len(amounts)
        if fn == "count":
            return len(amounts)
        if fn == "min":
            return min(amounts)
        if fn == "max":
            return max(amounts)

    return None
