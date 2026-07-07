def make_label(condition: dict) -> str:
    ctype = condition["type"]
    field = condition.get("field", condition.get("relationship", ""))
    op = condition.get("op", "")

    OP_TEXT = {
        "gt": ">",
        "gte": "≥",
        "lt": "<",
        "lte": "≤",
        "eq": "=",
        "neq": "≠",
        "equals": "=",
        "contains": "contains",
        "starts_with": "starts with",
        "in": "in",
        "not_in": "not in",
    }

    if ctype == "presence":
        return f"{field} is set"

    if ctype == "cross_field":
        field_a = condition.get("field_a", "")
        field_b = condition.get("field_b", "")
        return f"{field_a} {OP_TEXT.get(op, op)} {field_b}"

    if ctype in ("comparison", "string_match", "membership"):
        value = condition.get("value", condition.get("field_b", ""))
        return f"{field} {OP_TEXT.get(op, op)} {value}"

    if ctype == "count":
        filter_desc = ""
        if condition.get("filter"):
            k, v = next(iter(condition["filter"].items()))
            filter_desc = f" ({k}={v})"
        return f"{field}{filter_desc} count {OP_TEXT.get(op, op)} {condition.get('value')}"

    if ctype == "aggregate":
        return f"{condition.get('fn')}({field}) {OP_TEXT.get(op, op)} {condition.get('value')}"

    if ctype == "temporal":
        return f"{field} {op} {condition.get('value')}"

    return f"{ctype}: {field}"
