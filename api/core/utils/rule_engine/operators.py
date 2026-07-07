class UnknownOperatorError(ValueError):
    pass


OPERATORS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "equals": lambda a, b: str(a).strip().lower() == str(b).strip().lower(),
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "starts_with": lambda a, b: str(a).lower().startswith(str(b).lower()),
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "before": lambda a, b: a < b,
    "after": lambda a, b: a > b,
}


def apply_op(value, op: str, target) -> bool:
    if op not in OPERATORS:
        raise UnknownOperatorError(f"Unknown operator: '{op}'")

    try:
        return OPERATORS[op](value, target)
    except TypeError:
        return False
