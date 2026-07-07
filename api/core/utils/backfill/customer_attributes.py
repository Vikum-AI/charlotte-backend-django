import hashlib
from dataclasses import dataclass

from neomodel import db

BATCH_SIZE = 1000

INDUSTRIES = ('retail', 'finance', 'logistics', 'ecommerce', 'services')

FETCH_CUSTOMER_IDS_QUERY = """
MATCH (c:Customer)
WHERE $last_id IS NULL OR c.customer_id > $last_id
WITH c ORDER BY c.customer_id LIMIT $batch_size
RETURN c.customer_id AS customer_id
"""

CLEAR_LEGACY_KYC_TIER_QUERY = """
MATCH (c:Customer)
WHERE c.kyc_status IN ['basic', 'standard', 'enhanced']
SET c.kyc_status = null
"""

CUSTOMER_BACKFILL_QUERY = """
UNWIND $rows AS row
MATCH (c:Customer {customer_id: row.customer_id})
OPTIONAL MATCH (c)-[:OWNS]->(a:Account)-[:INITIATES]->(t:Transaction)
WITH c, count(t) AS tx_count, count(DISTINCT a) AS account_count, row.industry AS industry
SET c.risk_rating = CASE
      WHEN tx_count > 10 OR account_count > 1 THEN 'high'
      WHEN tx_count >= 3 AND tx_count <= 10 THEN 'medium'
      ELSE 'low'
    END,
    c.industry = industry
"""

KYC_DISTRIBUTION_QUERY = """
MATCH (c:Customer)
RETURN c.kyc_status AS value, count(*) AS count
ORDER BY count DESC
"""

RISK_DISTRIBUTION_QUERY = """
MATCH (c:Customer)
RETURN c.risk_rating AS value, count(*) AS count
ORDER BY count DESC
"""

NULL_COUNT_QUERY = """
MATCH (c:Customer)
WHERE c.kyc_status IS NULL OR c.risk_rating IS NULL OR c.industry IS NULL
RETURN count(c) AS count
"""

SAMPLE_CUSTOMERS_QUERY = """
MATCH (c:Customer)
RETURN c.customer_id AS customer_id,
       c.kyc_status AS kyc_status,
       c.risk_rating AS risk_rating,
       c.industry AS industry
ORDER BY c.customer_id
LIMIT 10
"""


@dataclass
class BackfillSummary:
    total_processed: int
    kyc_distribution: list[tuple[str | None, int]]
    risk_distribution: list[tuple[str | None, int]]
    null_count: int
    sample_customers: list[tuple[str, str, str, str]]


def industry_for(customer_id: str) -> str:
    digest = hashlib.sha256(customer_id.encode()).digest()
    return INDUSTRIES[int.from_bytes(digest[:4], 'big') % len(INDUSTRIES)]


def _fetch_customer_ids(last_id: str | None, batch_size: int) -> list[str]:
    results, _ = db.cypher_query(
        FETCH_CUSTOMER_IDS_QUERY,
        {'last_id': last_id, 'batch_size': batch_size},
    )
    return [row[0] for row in results]


def _backfill_batch(customer_ids: list[str]) -> None:
    rows = [
        {'customer_id': customer_id, 'industry': industry_for(customer_id)}
        for customer_id in customer_ids
    ]
    db.cypher_query(CUSTOMER_BACKFILL_QUERY, {'rows': rows})


def _fetch_distribution(query: str) -> list[tuple[str | None, int]]:
    results, _ = db.cypher_query(query)
    return [(row[0], row[1]) for row in results]


def _fetch_null_count() -> int:
    results, _ = db.cypher_query(NULL_COUNT_QUERY)
    return results[0][0] if results else 0


def _fetch_sample_customers() -> list[tuple[str, str, str, str]]:
    results, _ = db.cypher_query(SAMPLE_CUSTOMERS_QUERY)
    return [(row[0], row[1], row[2], row[3]) for row in results]


def _clear_legacy_kyc_tier_values() -> None:
    db.cypher_query(CLEAR_LEGACY_KYC_TIER_QUERY)


def backfill_customer_attributes(limit: int | None = None) -> BackfillSummary:
    _clear_legacy_kyc_tier_values()

    last_id = None
    total_processed = 0
    batch_index = 0

    while True:
        if limit is not None:
            remaining = limit - total_processed
            if remaining <= 0:
                break
            batch_size = min(BATCH_SIZE, remaining)
        else:
            batch_size = BATCH_SIZE

        customer_ids = _fetch_customer_ids(last_id, batch_size)
        if not customer_ids:
            break

        _backfill_batch(customer_ids)
        total_processed += len(customer_ids)
        batch_index += 1
        last_id = customer_ids[-1]
        print(f'  backfill: batch {batch_index} ({total_processed} customers processed)')

        if len(customer_ids) < batch_size:
            break

    return BackfillSummary(
        total_processed=total_processed,
        kyc_distribution=_fetch_distribution(KYC_DISTRIBUTION_QUERY),
        risk_distribution=_fetch_distribution(RISK_DISTRIBUTION_QUERY),
        null_count=_fetch_null_count(),
        sample_customers=_fetch_sample_customers(),
    )
