from api.core.models import Case, SuggestedSubRule


def is_suggested_sub_rule_applicable(
    suggested: SuggestedSubRule,
    case: Case,
) -> bool:
    transaction_ids = suggested.applicable_transaction_ids or []
    return not transaction_ids or case.transaction_id in transaction_ids
