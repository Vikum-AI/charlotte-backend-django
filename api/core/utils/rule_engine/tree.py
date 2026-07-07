from api.core.utils.rule_engine.conditions import CONDITION_RESOLVERS
from api.core.utils.rule_engine.types import FAIL, PASS, PENDING


def resolve_tree(node: dict, case_id: str, transaction_id: str, attached_evidence: list):
    if "all" in node:
        results = [
            resolve_tree(child, case_id, transaction_id, attached_evidence)
            for child in node["all"]
        ]
        statuses = [result[0] for result in results]
        leaves = [leaf for result in results for leaf in result[1]]

        if FAIL in statuses:
            return FAIL, leaves
        if PENDING in statuses:
            return PENDING, leaves
        return PASS, leaves

    if "any" in node:
        results = [
            resolve_tree(child, case_id, transaction_id, attached_evidence)
            for child in node["any"]
        ]
        statuses = [result[0] for result in results]
        leaves = [leaf for result in results for leaf in result[1]]

        if PASS in statuses:
            return PASS, leaves
        if PENDING in statuses:
            return PENDING, leaves
        return FAIL, leaves

    if "not" in node:
        inner = node["not"]
        target = inner[0] if isinstance(inner, list) else inner
        status, leaves = resolve_tree(target, case_id, transaction_id, attached_evidence)
        inverted = {PASS: FAIL, FAIL: PASS, PENDING: PENDING}[status]
        return inverted, leaves

    condition_type = node["type"]
    if condition_type not in CONDITION_RESOLVERS:
        raise ValueError(f"Unknown condition type: '{condition_type}'")

    result = CONDITION_RESOLVERS[condition_type](
        node,
        case_id,
        transaction_id,
        attached_evidence,
    )
    return result.status, [result]
