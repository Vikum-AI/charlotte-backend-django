APPROVAL_ROLE_RANK = {
    "admin": 1,
    "editor": 2,
    "viewer": 3,
    "restricted": 4,
}


def role_satisfies_filter(actual: str | None, required: str) -> bool:
    if actual is None:
        return False

    actual_normalized = str(actual).lower()
    required_normalized = str(required).lower()
    actual_rank = APPROVAL_ROLE_RANK.get(actual_normalized)
    required_rank = APPROVAL_ROLE_RANK.get(required_normalized)
    if actual_rank is None or required_rank is None:
        return actual_normalized == required_normalized

    return actual_rank <= required_rank


def payload_matches_filter(payload: dict, filter_spec: dict) -> bool:
    for key, expected in filter_spec.items():
        actual = payload.get(key)
        if key == "role":
            if not role_satisfies_filter(actual, expected):
                return False
        elif actual != expected:
            return False

    return True


def evidence_matches_filter(evidence, filter_spec: dict) -> bool:
    for key, expected in filter_spec.items():
        attr_value = getattr(evidence, key, None)
        payload_value = evidence.payload.get(key)
        if key == "role":
            actual = payload_value if payload_value is not None else attr_value
            if not role_satisfies_filter(actual, expected):
                return False
        elif attr_value != expected and payload_value != expected:
            return False

    return True
