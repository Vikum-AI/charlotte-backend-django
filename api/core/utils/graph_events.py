import json

import redis
from django.conf import settings


def publish_evidence_created(case_id: str, transaction_id: str, evidence) -> None:
    evidence_id = _evidence_value(evidence, "evidence_id")
    _publish_graph_delta(
        case_id,
        {
            "type": "graph_delta",
            "case_id": case_id,
            "nodes": [
                {
                    "id": evidence_id,
                    "label": "Evidence",
                    "properties": {
                        "evidence_type": _evidence_value(evidence, "evidence_type"),
                        "resolved_status": _evidence_value(evidence, "resolved_status"),
                        "source_text": _evidence_value(evidence, "source_text"),
                        "confidence": _evidence_value(evidence, "confidence"),
                    },
                }
            ],
            "edges": [
                {
                    "id": f"{evidence_id}->{transaction_id}",
                    "source": evidence_id,
                    "target": transaction_id,
                    "type": "SUPPORTS",
                }
            ],
        },
    )


def _evidence_value(evidence, field: str):
    if isinstance(evidence, dict):
        return evidence.get(field)
    return getattr(evidence, field)


def publish_evidence_status_delta(
    case_id: str,
    evidence_id: str,
    resolved_status: str,
) -> None:
    _publish_graph_delta(
        case_id,
        {
            "type": "graph_delta",
            "case_id": case_id,
            "nodes": [
                {
                    "id": evidence_id,
                    "label": "Evidence",
                    "properties": {"resolved_status": resolved_status},
                }
            ],
            "edges": [],
        },
    )


def _publish_graph_delta(case_id: str, payload: dict) -> None:
    client = redis.Redis.from_url(settings.DRAMATIQ_BROKER["OPTIONS"]["url"])
    client.xadd(
        f"case:{case_id}:graph",
        {"data": json.dumps(payload)},
        maxlen=500,
        approximate=True,
    )
