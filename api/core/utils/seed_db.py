from pathlib import Path

from neomodel import db

from api.core.graph.repository import (
    save_graph_enrichments,
    save_graph_transactions,
    save_graph_transfers,
)
from api.core.ingestion.transform import amlsim, banksim, transactions


def wipe_graph_if_populated() -> bool:
    results, _ = db.cypher_query(
        'MATCH (n) RETURN count(n) AS count LIMIT 1',
    )
    count = results[0][0] if results else 0
    if count == 0:
        return False

    db.clear_neo4j_database(clear_constraints=True, clear_indexes=True)
    return True


def _apply_limit(rows: list, limit: int | None) -> list:
    if limit is None:
        return rows
    return rows[:limit]


def load_dataset(name: str, path: Path, limit: int | None = None):
    loaders = {
        'transactions': _load_transactions,
        'banksim': _load_banksim,
        'amlsim': _load_amlsim,
    }
    loader = loaders.get(name)
    if loader is None:
        raise ValueError(f'Unknown dataset: {name}')
    loader(path, limit)


def _load_transactions(path: Path, limit: int | None):
    save_graph_transactions(
        _apply_limit(transactions.transform(path), limit))


def _load_banksim(path: Path, limit: int | None):
    save_graph_transactions(
        _apply_limit(banksim.transform_transactions(path), limit))
    save_graph_enrichments(
        _apply_limit(banksim.transform_enrichments(path), limit))


def _load_amlsim(path: Path, limit: int | None):
    save_graph_transfers(_apply_limit(amlsim.transform(path), limit))
