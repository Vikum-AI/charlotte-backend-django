from api.core.evidence.models import CaseEvidence


def attach_evidence(case_id: str, evidence_id: str) -> None:
    CaseEvidence.objects.get_or_create(
        case_id=case_id,
        evidence_id=evidence_id,
    )


def detach_evidence(case_id: str, evidence_id: str) -> None:
    CaseEvidence.objects.filter(
        case_id=case_id,
        evidence_id=evidence_id,
    ).delete()


def get_attached_evidence_ids(case_id: str) -> set[str]:
    return set(
        CaseEvidence.objects.filter(case_id=case_id).values_list(
            'evidence_id',
            flat=True,
        ),
    )
