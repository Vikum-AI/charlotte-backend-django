import csv
from pathlib import Path

from neomodel import db

BATCH_SIZE = 1000


def load_dataset(name: str, path: Path):
    loaders = {
        'transactions': load_transactions,
        'banksim': load_banksim,
        'amlsim': load_amlsim,
    }
    loader = loaders.get(name)
    if loader is None:
        raise ValueError(f'Unknown dataset: {name}')
    loader(path)


def load_transactions(path: Path):
    records = _read_csv_records(
        path,
        rename={
            'transactionid': 'transaction_id',
            'customerid': 'customer_id',
            'amount': 'amount',
            'currency': 'currency',
            'timestamp': 'timestamp',
        },
    )

    query = """
    UNWIND $rows AS row

    MERGE (c:Customer {customer_id: row.customer_id})

    MERGE (t:Transaction {transaction_id: row.transaction_id})
    SET t.amount = row.amount,
        t.currency = row.currency,
        t.timestamp = row.timestamp

    MERGE (c)-[:INITIATES]->(t)
    """
    run_batch(query, records, 'transactions')


def load_banksim(path: Path):
    records = _read_csv_records(path)

    query = """
    UNWIND $rows AS row

    MATCH (t:Transaction {transaction_id: row.transactionid})

    SET t.category = row.category,
        t.step = row.step,
        t.type = row.type
    """
    run_batch(query, records, 'banksim')


def load_amlsim(path: Path):
    records = _read_csv_records(path)

    query = """
    UNWIND $rows AS row

    MERGE (a:Account {account_id: row.account})
    MERGE (b:Account {account_id: row.target})

    MERGE (a)-[r:TRANSFER]->(b)
    SET r.amount = row.amount,
        r.timestamp = row.timestamp
    """
    run_batch(query, records, 'amlsim')


def _read_csv_records(path: Path, rename: dict | None = None) -> list[dict]:
    csv_file = next(path.glob('*.csv'))
    with csv_file.open(newline='', encoding='utf-8') as handle:
        records = []
        for row in csv.DictReader(handle):
            record = {}
            for column, value in row.items():
                key = column.lower()
                if rename and key in rename:
                    key = rename[key]
                record[key] = '' if value in (None, '') else value
            records.append(record)
        return records


def run_batch(query: str, records: list, label: str):
    for i in range(0, len(records), BATCH_SIZE):
        db.cypher_query(query, {'rows': records[i:i + BATCH_SIZE]})

    print(f'Loaded {label}: {len(records)} records')
