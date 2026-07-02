from neomodel import db
from api.core.utils.evidence.exceptions import EvidenceCreationError


def resolve_customer_id_for_transaction(transaction_id: str) -> str:
    results, _ = db.cypher_query(
        """
        MATCH (c:Customer)-[:OWNS]->(:Account)-[:INITIATES]->(t:Transaction {transaction_id: $tid})
        RETURN c.customer_id LIMIT 1
        """,
        {"tid": transaction_id},
    )

    if not results:
        raise EvidenceCreationError(
            f"Could not resolve Customer for transaction '{transaction_id}'")

    return results[0][0]
