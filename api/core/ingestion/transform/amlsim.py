from pathlib import Path

from api.core.ingestion.schemas import GraphTransferWrite
from api.core.ingestion.transform.csv_utils import (
    parse_float,
    read_csv_records,
    to_iso_timestamp,
)


def _load_account_customer_map(path: Path) -> dict[str, str]:
    records = read_csv_records(path, filename='accounts.csv')
    mapping = {}
    for record in records:
        account_id = record.get('account_id')
        customer_id = record.get('customer_id')
        if account_id and customer_id:
            mapping[str(account_id)] = str(customer_id)
    return mapping


def transform(path: Path) -> list[GraphTransferWrite]:
    account_customers = _load_account_customer_map(path)
    records = read_csv_records(path, filename='transactions.csv')
    results = []
    skipped = 0

    for record in records:
        source = record.get('sender_account_id')
        target = record.get('receiver_account_id')
        transaction_id = record.get('tx_id')
        if not source or not target or not transaction_id:
            skipped += 1
            continue

        customer_id = account_customers.get(str(source))
        if not customer_id:
            skipped += 1
            continue

        results.append(
            GraphTransferWrite(
                transaction_id=f'amlsim_{transaction_id}',
                customer_id=customer_id,
                source_account_id=str(source),
                target_account_id=str(target),
                source_account_role='source',
                target_account_role='counterparty',
                amount=parse_float(record.get('tx_amount')),
                timestamp_iso=to_iso_timestamp(record.get('timestamp')),
            ),
        )

    if skipped:
        print(f'  skipped {skipped} transfer rows (missing fields or customer lookup)')

    return results
