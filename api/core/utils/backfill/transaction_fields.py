from dataclasses import dataclass, field

from neomodel import db

from api.core.utils.backfill.derivations import BACKFILL_FIELDS, DERIVE_BY_FIELD

DEFAULT_BATCH_SIZE = 500

DRY_RUN_QUERY = """
MATCH (t:Transaction)
RETURN
  count(CASE WHEN t.currency IS NULL THEN 1 END) AS currency,
  count(CASE WHEN t.timestamp IS NULL THEN 1 END) AS timestamp,
  count(CASE WHEN t.status IS NULL THEN 1 END) AS status,
  count(CASE WHEN t.channel IS NULL THEN 1 END) AS channel,
  count(CASE WHEN t.category IS NULL THEN 1 END) AS category,
  count(CASE WHEN t.type IS NULL THEN 1 END) AS type
"""

FETCH_BATCH_QUERY = """
MATCH (t:Transaction)
WHERE ($last_id IS NULL OR t.transaction_id > $last_id)
  AND (t.currency IS NULL OR t.timestamp IS NULL OR t.status IS NULL
       OR t.channel IS NULL OR t.category IS NULL OR t.type IS NULL)
WITH t ORDER BY t.transaction_id LIMIT $batch_size
RETURN t.transaction_id AS transaction_id,
       t.currency AS currency,
       t.timestamp AS timestamp,
       t.status AS status,
       t.channel AS channel,
       t.category AS category,
       t.type AS type,
       coalesce(t.synthetic_fields, []) AS synthetic_fields
"""

BACKFILL_WRITE_QUERY = """
UNWIND $rows AS row
MATCH (t:Transaction {transaction_id: row.transaction_id})
SET t.currency = coalesce(t.currency, row.currency),
    t.timestamp = coalesce(
        t.timestamp,
        CASE WHEN row.timestamp_iso IS NULL THEN null ELSE datetime(row.timestamp_iso) END
    ),
    t.status = coalesce(t.status, row.status),
    t.channel = coalesce(t.channel, row.channel),
    t.category = coalesce(t.category, row.category),
    t.type = coalesce(t.type, row.type),
    t.synthetic_fields = CASE
      WHEN size(row.new_synthetic_fields) > 0
      THEN coalesce(t.synthetic_fields, []) + row.new_synthetic_fields
      ELSE t.synthetic_fields
    END
"""


@dataclass
class BackfillSummary:
    total_processed: int
    backfilled_per_field: dict[str, int] = field(default_factory=dict)


def dry_run_missing_counts() -> dict[str, int]:
    results, _ = db.cypher_query(DRY_RUN_QUERY)
    if not results:
        return {field_name: 0 for field_name in BACKFILL_FIELDS}

    row = results[0]
    return {field_name: row[index] for index, field_name in enumerate(BACKFILL_FIELDS)}


def _fetch_batch(last_id: str | None, batch_size: int) -> list[dict]:
    results, _ = db.cypher_query(
        FETCH_BATCH_QUERY,
        {'last_id': last_id, 'batch_size': batch_size},
    )
    batches = []
    for row in results:
        batches.append({
            'transaction_id': row[0],
            'currency': row[1],
            'timestamp': row[2],
            'status': row[3],
            'channel': row[4],
            'category': row[5],
            'type': row[6],
            'synthetic_fields': row[7] or [],
        })
    return batches


def _build_backfill_row(record: dict) -> tuple[dict, list[str]]:
    transaction_id = record['transaction_id']
    row: dict = {
        'transaction_id': transaction_id,
        'new_synthetic_fields': [],
    }
    new_fields: list[str] = []

    for field_name in BACKFILL_FIELDS:
        if record.get(field_name) is not None:
            continue

        derived = DERIVE_BY_FIELD[field_name](transaction_id)
        if field_name == 'timestamp':
            row['timestamp_iso'] = derived
        else:
            row[field_name] = derived
        new_fields.append(field_name)

    row['new_synthetic_fields'] = new_fields
    return row, new_fields


def _backfill_batch(records: list[dict]) -> list[str]:
    rows = []
    all_new_fields: list[str] = []
    for record in records:
        row, new_fields = _build_backfill_row(record)
        if not new_fields:
            continue
        rows.append(row)
        all_new_fields.extend(new_fields)

    if rows:
        db.cypher_query(BACKFILL_WRITE_QUERY, {'rows': rows})

    return all_new_fields


def backfill_transaction_fields(batch_size: int = DEFAULT_BATCH_SIZE) -> BackfillSummary:
    last_id = None
    total_processed = 0
    batch_index = 0
    backfilled_per_field = {field_name: 0 for field_name in BACKFILL_FIELDS}

    while True:
        records = _fetch_batch(last_id, batch_size)
        if not records:
            break

        new_fields = _backfill_batch(records)
        for field_name in new_fields:
            backfilled_per_field[field_name] += 1

        total_processed += len(records)
        batch_index += 1
        last_id = records[-1]['transaction_id']
        print(f'  backfill: batch {batch_index} ({total_processed} transactions processed)')

        if len(records) < batch_size:
            break

    return BackfillSummary(
        total_processed=total_processed,
        backfilled_per_field=backfilled_per_field,
    )
