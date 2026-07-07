from neomodel import db

from api.core.models import Case
from api.core.utils.evidence.case_scope import get_attached_evidence_ids

CASE_GRAPH_QUERY = """
MATCH (c:Customer)-[:OWNS]->(a:Account)-[:INITIATES]->(t:Transaction {transaction_id: $transaction_id})
OPTIONAL MATCH (e:Evidence)-[:SUPPORTS]->(t)
WHERE e.evidence_id IN $attached_evidence_ids
  AND e.case_id = $case_id
RETURN
    c.customer_id AS customer_id,
    c.kyc_status AS customer_kyc_status,
    c.risk_rating AS customer_risk_rating,
    c.industry AS customer_industry,
    a.account_id AS account_id,
    a.role AS account_role,
    a.type AS account_type,
    a.status AS account_status,
    t.transaction_id AS transaction_id,
    t.amount AS transaction_amount,
    t.currency AS transaction_currency,
    t.status AS transaction_status,
    t.channel AS transaction_channel,
    collect({
        evidence_id: e.evidence_id,
        evidence_type: e.evidence_type,
        resolved_status: e.resolved_status,
        source_text: e.source_text,
        confidence: e.confidence
    }) AS evidence_nodes
"""


def get_case_graph_snapshot(case_id: str) -> dict:
    case = Case.objects.get(id=case_id)
    attached_evidence_ids = list(get_attached_evidence_ids(case_id))

    results, _ = db.cypher_query(
        CASE_GRAPH_QUERY,
        {
            "case_id": case_id,
            "transaction_id": case.transaction_id,
            "attached_evidence_ids": attached_evidence_ids,
        },
    )

    nodes_by_id = {}
    edges_by_id = {}

    for row in results:
        (
            customer_id,
            customer_kyc_status,
            customer_risk_rating,
            customer_industry,
            account_id,
            account_role,
            account_type,
            account_status,
            transaction_id,
            transaction_amount,
            transaction_currency,
            transaction_status,
            transaction_channel,
            evidence_nodes,
        ) = row

        _put_node(
            nodes_by_id,
            customer_id,
            "Customer",
            {
                "kyc_status": customer_kyc_status,
                "risk_rating": customer_risk_rating,
                "industry": customer_industry,
            },
        )
        _put_node(
            nodes_by_id,
            account_id,
            "Account",
            {
                "role": account_role,
                "type": account_type,
                "status": account_status,
            },
        )
        _put_node(
            nodes_by_id,
            transaction_id,
            "Transaction",
            {
                "amount": transaction_amount,
                "currency": transaction_currency,
                "status": transaction_status,
                "channel": transaction_channel,
            },
        )
        _put_edge(edges_by_id, customer_id, account_id, "OWNS")
        _put_edge(edges_by_id, account_id, transaction_id, "INITIATES")

        for evidence in evidence_nodes:
            evidence_id = evidence.get("evidence_id")
            if evidence_id is None:
                continue

            _put_node(
                nodes_by_id,
                evidence_id,
                "Evidence",
                {
                    "evidence_type": evidence.get("evidence_type"),
                    "resolved_status": evidence.get("resolved_status"),
                    "source_text": evidence.get("source_text"),
                    "confidence": evidence.get("confidence"),
                },
            )
            _put_edge(edges_by_id, evidence_id, transaction_id, "SUPPORTS")

    return {
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_id.values()),
    }


def _put_node(nodes_by_id: dict, node_id: str, label: str, properties: dict) -> None:
    nodes_by_id[node_id] = {
        "id": node_id,
        "label": label,
        "properties": properties,
    }


def _put_edge(edges_by_id: dict, source_id: str, target_id: str, edge_type: str) -> None:
    edge_id = f"{source_id}->{target_id}"
    edges_by_id[edge_id] = {
        "id": edge_id,
        "source": source_id,
        "target": target_id,
        "type": edge_type,
    }
