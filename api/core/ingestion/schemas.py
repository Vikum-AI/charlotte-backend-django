from dataclasses import dataclass


@dataclass
class GraphTransactionWrite:
    transaction_id: str
    customer_id: str
    account_id: str
    account_role: str
    amount: float | None
    currency: str | None
    timestamp_iso: str | None
    channel: str | None
    category: str | None


@dataclass
class GraphTransferWrite:
    transaction_id: str
    customer_id: str
    source_account_id: str
    target_account_id: str
    source_account_role: str
    target_account_role: str
    amount: float | None
    timestamp_iso: str | None


@dataclass
class GraphEnrichmentWrite:
    transaction_id: str
    category: str | None
    step: str | None
    type: str | None
