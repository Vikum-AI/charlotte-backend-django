from pathlib import Path

from api.core.ingestion.schemas import GraphTransactionWrite
from api.core.ingestion.transform.csv_utils import (
    derive_account_id,
    parse_float,
    read_csv_records,
    to_iso_timestamp,
)

DATASET = 'transactions'


def transform(path: Path) -> list[GraphTransactionWrite]:
    records = read_csv_records(path, filename='transactions.csv')
    results = []
    skipped = 0

    for record in records:
        transaction_id = record.get('transaction_id')
        customer_id = record.get('customer_id')
        if not transaction_id or not customer_id:
            skipped += 1
            continue

        results.append(
            GraphTransactionWrite(
                transaction_id=str(transaction_id),
                customer_id=str(customer_id),
                account_id=derive_account_id(DATASET, str(customer_id)),
                account_role='source',
                amount=parse_float(record.get('amount')),
                currency=record.get('currency') or None,
                timestamp_iso=to_iso_timestamp(
                    record.get('transaction_timestamp') or record.get('timestamp')),
                channel=record.get('merchant_category') or None,
                category=None,
            ),
        )

    if skipped:
        print(f'  skipped {skipped} rows (missing transaction_id or customer_id)')

    return results
