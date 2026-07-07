import json

import dramatiq
import redis
from django.conf import settings
from django.utils import timezone

from api.core.utils.rule_engine.evaluate import evaluate_rule


@dramatiq.actor
def recompute_rule_evaluation(case_rule_id: str):
    from api.core.models import CaseRule

    case_rule = CaseRule.objects.select_related("case", "evaluation").get(id=case_rule_id)
    result = evaluate_rule(case_rule)

    evaluation = case_rule.evaluation
    evaluation.status = result.status
    evaluation.leaf_results = result.leaf_results
    evaluation.reason = result.reason
    evaluation.evidence_used = result.evidence_used
    evaluation.is_stale = False
    evaluation.computed_at = timezone.now()
    evaluation.save()

    client = redis.Redis.from_url(settings.DRAMATIQ_BROKER["OPTIONS"]["url"])
    client.xadd(
        f"case:{case_rule.case_id}:status",
        {
            "data": json.dumps({
                "type": "rule_updated",
                "rule_id": case_rule.rule_id,
                "status": result.status,
                "leaf_results": result.leaf_results,
                "reason": result.reason,
            }),
        },
        maxlen=500,
        approximate=True,
    )
