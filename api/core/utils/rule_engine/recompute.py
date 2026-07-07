from api.core.models import CaseRule
from api.core.tasks.rule_evaluation_tasks import recompute_rule_evaluation


def recompute_rules_for_case_sync(case) -> None:
    for case_rule in CaseRule.objects.filter(case=case):
        recompute_rule_evaluation.fn(str(case_rule.id))
