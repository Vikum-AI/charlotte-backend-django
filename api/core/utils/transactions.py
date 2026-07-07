from neomodel import db


def transaction_exists(transaction_id: str) -> bool:
    results, _ = db.cypher_query(
        """
        MATCH (t:Transaction {transaction_id: $transaction_id})
        RETURN count(t) > 0
        """,
        {"transaction_id": transaction_id},
    )
    return bool(results and results[0][0])


def transaction_ids_matching_case_search(q: str) -> list[str]:
    cypher = """
    MATCH (t:Transaction)
    OPTIONAL MATCH (c:Customer)-[:OWNS]->(:Account)-[:INITIATES]->(t)
    WHERE toString(t.amount) CONTAINS $q
       OR toLower(coalesce(c.name, "")) CONTAINS toLower($q)
    RETURN t.transaction_id AS transaction_id
    """
    results, _ = db.cypher_query(cypher, {"q": q})
    return [row[0] for row in results if row[0]]
