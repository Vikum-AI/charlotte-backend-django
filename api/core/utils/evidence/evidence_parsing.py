import re

APPROVAL_KEYWORDS = ["approved by", "approval", "approver"]
KYC_KEYWORDS = ["kyc status", "kyc verification", "verification status"]

EMAIL_PATTERN = r'[\w\.-]+@[\w\.-]+'
DATE_PATTERN = r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}'
KYC_STATUS_PATTERN = r'VERIFIED|PENDING|REJECTED'


def find_near_keyword(text: str, keywords: list[str], value_pattern: str, window: int = 200) -> str | None:
    lowered = text.lower()

    for kw in keywords:
        idx = lowered.find(kw.lower())

        if idx == -1:
            continue

        snippet = text[idx: idx + window]
        match = re.search(value_pattern, snippet, re.IGNORECASE)

        if match:
            return match.group()

    return None


def extract_containing_sentence(text: str, anchor: str) -> str | None:
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if anchor.lower() in sentence.lower():
            return sentence.strip()

    return None


def detect_evidence_type(text: str) -> str:
    lowered = text.lower()

    if any(kw in lowered for kw in APPROVAL_KEYWORDS):
        return "approval"

    if any(kw in lowered for kw in KYC_KEYWORDS):
        return "kyc_status"

    return "custom"
