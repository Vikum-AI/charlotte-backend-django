from dataclasses import dataclass


@dataclass
class ResolutionResult:
    status: str
    reason: str | None = None
    resolved_payload: dict | None = None
