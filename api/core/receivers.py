from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from api.core.models import CaseEvidence, CaseRule, CaseRuleEvaluation, Status
from api.core.tasks.rule_evaluation_tasks import recompute_rule_evaluation


@receiver(post_save, sender=CaseRule)
def mark_evaluation_stale_on_rule_save(sender, instance, created, **kwargs):
    del sender, kwargs

    evaluation, _ = CaseRuleEvaluation.objects.get_or_create(
        case_rule=instance,
        defaults={
            "status": Status.PENDING,
            "leaf_results": [],
            "is_stale": True,
        },
    )

    if not created:
        evaluation.is_stale = True
        evaluation.save(update_fields=["is_stale"])

    recompute_rule_evaluation.send(str(instance.id))


@receiver(post_save, sender=CaseEvidence)
@receiver(post_delete, sender=CaseEvidence)
def mark_rules_stale_on_evidence_change(sender, instance, **kwargs):
    del sender, kwargs

    mark_rules_stale_for_case(instance.case)


def mark_rules_stale_for_case(case):
    rules = CaseRule.objects.filter(case=case).select_related("evaluation")

    for case_rule in rules:
        evaluation = getattr(case_rule, "evaluation", None)
        if evaluation is None:
            evaluation, _ = CaseRuleEvaluation.objects.get_or_create(
                case_rule=case_rule,
                defaults={
                    "status": Status.PENDING,
                    "leaf_results": [],
                    "is_stale": True,
                },
            )
        elif not evaluation.is_stale:
            evaluation.is_stale = True
            evaluation.save(update_fields=["is_stale"])

        recompute_rule_evaluation.send(str(case_rule.id))
