import logging
import mimetypes
import tempfile
from pathlib import Path
from uuid import uuid4

import dramatiq
import requests

from api.core.models import Case, CaseEvidence
from api.core.utils.evidence.create import (
    create_approval_evidence,
    create_custom_evidence,
    create_kyc_evidence,
)
from api.core.utils.evidence.db_resolvers import resolve_customer_id_for_transaction
from api.core.utils.evidence.document_extraction import (
    extract_data_from_ocr,
    extract_data_from_transform,
)
from api.core.utils.evidence.evidence_parsing import (
    APPROVAL_KEYWORDS,
    DATE_PATTERN,
    KYC_KEYWORDS,
    KYC_STATUS_PATTERN,
    detect_evidence_type,
    extract_approver_email,
    extract_containing_sentence,
    find_near_keyword,
)
from api.core.utils.evidence.exceptions import EvidenceCreationError
from api.core.utils.graph_events import publish_evidence_created

TRANSFORM_CONFIDENCE = 0.85
OCR_CONFIDENCE = 0.6
SUPPORTED_DOCUMENT_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
}

logger = logging.getLogger(__name__)


@dramatiq.actor(throws=(EvidenceCreationError,))
def create_evidence_object(case_id, extracted_data: dict, evidence_metadata: dict | None = None):
    text = extracted_data["text"]
    evidence_metadata = evidence_metadata or {}

    try:
        case = Case.objects.get(id=case_id)
    except Case.DoesNotExist as exc:
        raise EvidenceCreationError(f"Case '{case_id}' not found") from exc

    transaction_id = case.transaction_id
    evidence_type = evidence_metadata.get("evidence_type_hint") or detect_evidence_type(text)
    evidence_id = str(uuid4())
    confidence = TRANSFORM_CONFIDENCE if extracted_data["method"] == "transform" else OCR_CONFIDENCE
    source_document_id = evidence_metadata.get("file_url") or case_id
    file_key = evidence_metadata.get("file_key")

    if evidence_type == "approval":
        approver_email = extract_approver_email(text)
        approval_date = find_near_keyword(
            text, APPROVAL_KEYWORDS + ["date"], DATE_PATTERN)
        
        source_text = extract_containing_sentence(text, "approv")
        
        evidence = create_approval_evidence(
            evidence_id=evidence_id, case_id=case_id, transaction_id=transaction_id,
            source_document_id=source_document_id, source_text=source_text or "",
            approver_email=approver_email, approval_date=approval_date,
            confidence=confidence, raw_extraction=extracted_data,
            file_key=file_key,
        )

    elif evidence_type == "kyc_status":
        kyc_status_value = find_near_keyword(
            text, KYC_KEYWORDS, KYC_STATUS_PATTERN)
        if kyc_status_value is not None:
            kyc_status_value = kyc_status_value.lower()
        verification_date = find_near_keyword(
            text, KYC_KEYWORDS + ["verified on"], DATE_PATTERN)
        
        source_text = extract_containing_sentence(text, "kyc")

        customer_id = resolve_customer_id_for_transaction(
            transaction_id)

        evidence = create_kyc_evidence(
            evidence_id=evidence_id, case_id=case_id, customer_id=customer_id,
            transaction_id=transaction_id,
            source_document_id=source_document_id, source_text=source_text or "",
            kyc_status_value=kyc_status_value, verification_date=verification_date,
            confidence=confidence, raw_extraction=extracted_data,
            file_key=file_key,
        )

    elif evidence_type == "custom":
        field_path = evidence_metadata.get("field_path")
        extracted_value = evidence_metadata.get("extracted_value")
        if not field_path:
            raise EvidenceCreationError("Custom evidence requires a field_path")
        if extracted_value is None:
            raise EvidenceCreationError("Custom evidence requires an extracted_value")

        evidence = create_custom_evidence(
            evidence_id=evidence_id,
            case_id=case_id,
            transaction_id=transaction_id,
            field_path=field_path,
            source_document_id=source_document_id,
            source_text=text,
            extracted_value=str(extracted_value),
            confidence=confidence,
            raw_extraction=extracted_data,
            file_key=file_key,
        )

    else:
        raise EvidenceCreationError(
            f"Unsupported evidence_type_hint '{evidence_type}'"
        )

    _, attached = CaseEvidence.objects.get_or_create(
        case=case, evidence_id=evidence.evidence_id)
    if attached:
        publish_evidence_created(case_id, transaction_id, evidence)
    
    return evidence


@dramatiq.actor
def extract_data_from_evidence(
    case_id,
    evidence_link: str,
    evidence_metadata: dict | None = None,
):
    evidence_metadata = evidence_metadata or {}
    response = requests.get(evidence_link, stream=True)
    response.raise_for_status()

    chunks = response.iter_content(chunk_size=8192)
    first_chunk = next((chunk for chunk in chunks if chunk), b"")
    suffix = _download_suffix(response, evidence_link, evidence_metadata, first_chunk)
    if not first_chunk or suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        logger.warning(
            "Skipping evidence extraction for unsupported download: "
            "case_id=%s url=%s content_type=%s suffix=%s",
            case_id,
            evidence_link,
            response.headers.get("content-type"),
            suffix,
        )
        return

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(first_chunk)
        for chunk in chunks:
            if not chunk:
                continue
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

    create_evidence_object.send(case_id, extracted_data, evidence_metadata)


def _download_suffix(
    response,
    evidence_link: str,
    evidence_metadata: dict,
    first_chunk: bytes,
) -> str:
    if first_chunk.startswith(b"%PDF"):
        return ".pdf"

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    suffix = mimetypes.guess_extension(content_type) if content_type else None
    if suffix == ".jpe":
        suffix = ".jpg"
    if suffix in SUPPORTED_DOCUMENT_SUFFIXES:
        return suffix
    if suffix and content_type not in {"application/octet-stream", "binary/octet-stream"}:
        return suffix

    for candidate in (evidence_metadata.get("file_key"), evidence_link.split("?", 1)[0]):
        if not candidate:
            continue
        suffix = Path(candidate).suffix.lower()
        if suffix in SUPPORTED_DOCUMENT_SUFFIXES:
            return suffix

    return suffix or Path(evidence_link.split("?", 1)[0]).suffix.lower() or ".bin"
