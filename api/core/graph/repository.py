from dataclasses import asdict

from neomodel import db

from api.core.ingestion.schemas import (
    GraphEnrichmentWrite,
    GraphTransactionWrite,
    GraphTransferWrite,
)

BATCH_SIZE = 1000
PROGRESS_EVERY_BATCHES = 50

TRANSACTION_WRITE_QUERY = """
UNWIND $rows AS row
MERGE (c:Customer {customer_id: row.customer_id})
MERGE (a:Account {account_id: row.account_id})
SET a.role = row.account_role
MERGE (t:Transaction {transaction_id: row.transaction_id})
SET t.amount = row.amount,
    t.currency = row.currency,
    t.timestamp = CASE
        WHEN row.timestamp_iso IS NULL THEN null
        ELSE datetime(row.timestamp_iso)
    END,
    t.channel = row.channel,
    t.category = row.category
MERGE (c)-[:OWNS]->(a)
MERGE (a)-[:INITIATES]->(t)
"""

TRANSFER_WRITE_QUERY = """
UNWIND $rows AS row
MERGE (c:Customer {customer_id: row.customer_id})
MERGE (source:Account {account_id: row.source_account_id})
SET source.role = row.source_account_role
MERGE (target:Account {account_id: row.target_account_id})
SET target.role = row.target_account_role
MERGE (t:Transaction {transaction_id: row.transaction_id})
SET t.amount = row.amount,
    t.timestamp = CASE
        WHEN row.timestamp_iso IS NULL THEN null
        ELSE datetime(row.timestamp_iso)
    END
MERGE (c)-[:OWNS]->(source)
MERGE (source)-[:INITIATES]->(t)
"""

ENRICHMENT_WRITE_QUERY = """
UNWIND $rows AS row
MATCH (t:Transaction {transaction_id: row.transaction_id})
SET t.category = coalesce(row.category, t.category),
    t.step = coalesce(row.step, t.step),
    t.type = coalesce(row.type, t.type)
"""


def _run_batch(query: str, rows: list[dict], label: str):
    if not rows:
        return

    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_index, start in enumerate(range(0, len(rows), BATCH_SIZE), start=1):
        db.cypher_query(query, {'rows': rows[start:start + BATCH_SIZE]})
        if batch_index % PROGRESS_EVERY_BATCHES == 0 or batch_index == total_batches:
            print(f'  {label}: batch {batch_index}/{total_batches}')


def save_graph_transactions(rows: list[GraphTransactionWrite]):
    dict_rows = [asdict(row) for row in rows]
    _run_batch(TRANSACTION_WRITE_QUERY, dict_rows, 'transactions')
    print(f'Loaded transactions: {len(rows)} records')


def save_graph_transfers(rows: list[GraphTransferWrite]):
    dict_rows = [asdict(row) for row in rows]
    _run_batch(TRANSFER_WRITE_QUERY, dict_rows, 'transfers')
    print(f'Loaded transfers: {len(rows)} records')


def save_graph_enrichments(rows: list[GraphEnrichmentWrite]):
    dict_rows = [asdict(row) for row in rows]
    _run_batch(ENRICHMENT_WRITE_QUERY, dict_rows, 'enrichments')
    print(f'Enriched transactions: {len(rows)} records')
