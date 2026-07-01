from pathlib import Path

from api.core.ingestion.schemas import GraphEnrichmentWrite, GraphTransactionWrite
from api.core.ingestion.transform.csv_utils import (
    clean_string,
    derive_account_id,
    parse_float,
    read_csv_records,
)

DATASET = 'banksim'


def transform_enrichments(path: Path) -> list[GraphEnrichmentWrite]:
    records = read_csv_records(path, filename='bs140513_032310.csv')
    results = []
    skipped = 0

    for index, record in enumerate(records):
        customer = clean_string(record.get('customer'))
        if not customer:
            skipped += 1
            continue

        results.append(
            GraphEnrichmentWrite(
                transaction_id=f'banksim_{customer}_{record["step"]}_{index}',
                category=clean_string(record.get('category')),
                step=record.get('step') or None,
                type=record.get('type') or None,
            ),
        )

    if skipped:
        print(f'  skipped {skipped} enrichment rows (missing customer)')

    return results


def transform_transactions(path: Path) -> list[GraphTransactionWrite]:
    records = read_csv_records(path, filename='bs140513_032310.csv')
    results = []
    skipped = 0

    for index, record in enumerate(records):
        customer = clean_string(record.get('customer'))
        if not customer:
            skipped += 1
            continue

        results.append(
            GraphTransactionWrite(
                transaction_id=f'banksim_{customer}_{record["step"]}_{index}',
                customer_id=customer,
                account_id=derive_account_id(DATASET, customer),
                account_role='source',
                amount=parse_float(record.get('amount')),
                currency=None,
                timestamp_iso=None,
                channel=None,
                category=clean_string(record.get('category')),
            ),
        )

    if skipped:
        print(f'  skipped {skipped} transaction rows (missing customer)')

    return results
