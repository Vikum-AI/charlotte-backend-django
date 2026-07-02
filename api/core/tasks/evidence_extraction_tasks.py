import tempfile
from pathlib import Path
from uuid import uuid4

import dramatiq
import requests

from api.core.models import Case, CaseEvidence
from api.core.utils.evidence.create import create_approval_evidence, create_kyc_evidence
from api.core.utils.evidence.db_resolvers import resolve_customer_id_for_transaction
from api.core.utils.evidence.document_extraction import (
    extract_data_from_ocr,
    extract_data_from_transform,
)
from api.core.utils.evidence.evidence_parsing import (
    APPROVAL_KEYWORDS,
    DATE_PATTERN,
    EMAIL_PATTERN,
    KYC_KEYWORDS,
    KYC_STATUS_PATTERN,
    detect_evidence_type,
    extract_containing_sentence,
    find_near_keyword,
)
from api.core.utils.evidence.exceptions import EvidenceCreationError

TRANSFORM_CONFIDENCE = 0.85
OCR_CONFIDENCE = 0.6


@dramatiq.actor
def create_evidence_object(case_id, extracted_data: dict):
    text = extracted_data["text"]

    try:
        case = Case.objects.get(id=case_id)
    except Case.DoesNotExist as exc:
        raise EvidenceCreationError(f"Case '{case_id}' not found") from exc

    transaction_id = case.transaction_id
    evidence_type = detect_evidence_type(text)
    evidence_id = str(uuid4())
    confidence = TRANSFORM_CONFIDENCE if extracted_data["method"] == "transform" else OCR_CONFIDENCE

    if evidence_type == "approval":
        approver_email = find_near_keyword(
            text, APPROVAL_KEYWORDS, EMAIL_PATTERN)
        approval_date = find_near_keyword(
            text, APPROVAL_KEYWORDS + ["date"], DATE_PATTERN)
        
        source_text = extract_containing_sentence(text, "approv")
        
        evidence = create_approval_evidence(
            evidence_id=evidence_id, transaction_id=transaction_id,
            source_document_id=case_id, source_text=source_text or "",
            approver_email=approver_email, approval_date=approval_date,
            confidence=confidence, raw_extraction=extracted_data,
        )

    elif evidence_type == "kyc_status":
        kyc_status_value = find_near_keyword(
            text, KYC_KEYWORDS, KYC_STATUS_PATTERN)
        verification_date = find_near_keyword(
            text, KYC_KEYWORDS + ["verified on"], DATE_PATTERN)
        
        source_text = extract_containing_sentence(text, "kyc")

        customer_id = resolve_customer_id_for_transaction(
            transaction_id)

        evidence = create_kyc_evidence(
            evidence_id=evidence_id, customer_id=customer_id, transaction_id=transaction_id,
            source_document_id=case_id, source_text=source_text or "",
            kyc_status_value=kyc_status_value, verification_date=verification_date,
            confidence=confidence, raw_extraction=extracted_data,
        )

    else:
        raise EvidenceCreationError(
            "Custom evidence requires a field_path, which isn't available in this pipeline yet."
        )

    CaseEvidence.objects.get_or_create(
        case=case, evidence_id=evidence.evidence_id)
    
    return evidence


@dramatiq.actor
def extract_data_from_evidence(case_id, evidence_link: str):
    response = requests.get(evidence_link, stream=True)
    response.raise_for_status()

    suffix = Path(evidence_link.split('?')[0]).suffix or '.bin'

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)

        tmp_path = tmp.name

    extracted_data = None

    try:
        try:
            extracted_data = extract_data_from_transform(tmp_path)
        except Exception:
            extracted_data = extract_data_from_ocr(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    create_evidence_object.send(case_id, extracted_data)
