from django.utils import timezone

from api.core.graph.models.investigation import Evidence
from api.core.models import CaseEvidence
from api.core.utils.evidence.exceptions import EvidenceConfirmationError
from api.core.utils.graph_events import publish_evidence_status_delta
from api.core.utils.rule_engine.recompute import recompute_rules_for_case_sync


def confirm_provisional_evidence(evidence_id: str, confirmed_by_user_id: str) -> None:
    try:
        evidence = Evidence.nodes.get(evidence_id=evidence_id)
    except Evidence.DoesNotExist as exc:
        raise EvidenceConfirmationError(f"Evidence '{evidence_id}' not found") from exc

    if evidence.resolved_status != "PROVISIONAL":
        raise EvidenceConfirmationError(
            f"Only PROVISIONAL evidence can be confirmed; "
            f"'{evidence_id}' is {evidence.resolved_status}"
        )

    evidence.resolved_status = "MATCHED"
    evidence.confirmed_at = timezone.now()
    evidence.confirmed_by = confirmed_by_user_id
    evidence.save()

    attached_rows = CaseEvidence.objects.filter(
        evidence_id=evidence_id,
    ).select_related("case")
    cases = []
    for attachment in attached_rows:
        publish_evidence_status_delta(
            attachment.case_id,
            evidence_id,
            "MATCHED",
        )
        cases.append(attachment.case)

    for case in cases:
        recompute_rules_for_case_sync(case)
