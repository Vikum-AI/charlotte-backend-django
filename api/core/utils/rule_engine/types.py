from dataclasses import dataclass, field

PASS, FAIL, PENDING = "PASS", "FAIL", "PENDING"
STATUSES = {PASS, FAIL, PENDING}


@dataclass
class ConditionResult:
    status: str
    label: str
    evidence_used: list[str] = field(default_factory=list)
    detail: str | None = None


@dataclass
class RuleEvaluationResult:
    status: str
    leaf_results: list[dict]
    reason: str
    evidence_used: list[str]
