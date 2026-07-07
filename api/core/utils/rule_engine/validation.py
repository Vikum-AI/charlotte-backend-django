import re
from collections.abc import Mapping

from api.core.utils.rule_engine.operators import OPERATORS


LEAF_REQUIRED_FIELDS = {
    "comparison": ("field", "op", "value"),
    "presence": ("field",),
    "membership": ("field", "op", "values"),
    "string_match": ("field", "op", "value"),
    "cross_field": ("field_a", "op", "field_b"),
    "temporal": ("field", "op", "value"),
    "count": ("relationship", "op", "value"),
    "aggregate": ("relationship", "field", "fn", "op", "value"),
}

TEMPORAL_OPERATORS = {*OPERATORS, "within_last"}
EVIDENCE_TYPES = frozenset({"approval", "kyc_status", "custom"})
EVIDENCE_FILTER_KEYS = frozenset({"role", "approver_email"})
AGGREGATE_FNS = frozenset({"sum", "avg", "count", "min", "max"})
AGGREGATE_RELATIONSHIPS = frozenset({"approvals", "transactions"})
AGGREGATE_FIELDS = frozenset({"amount"})


class ConditionValidationError(ValueError):
    ...


def validate_condition_tree(definition) -> None:
    if not isinstance(definition, Mapping):
        raise ConditionValidationError(
            "Rule definition must be a JSON object.")

    _validate_condition_node(definition)


def _validate_condition_node(node) -> None:
    if not isinstance(node, Mapping):
        raise ConditionValidationError(
            "Each condition node must be a JSON object.")

    root_keys = {"all", "any", "not", "type"} & node.keys()
    if not root_keys:
        raise ConditionValidationError(
            "Condition node must contain one of: all, any, not, type."
        )

    if len(root_keys) > 1:
        raise ConditionValidationError(
            "Condition node must contain only one root key among all, any, not, type."
        )

    if "all" in node or "any" in node:
        key = "all" if "all" in node else "any"
        children = node[key]

        if not isinstance(children, list) or not children:
            raise ConditionValidationError(
                f"'{key}' must be a non-empty list.")

        for child in children:
            _validate_condition_node(child)

        return

    if "not" in node:
        child = node["not"]

        if isinstance(child, list):
            if len(child) != 1:
                raise ConditionValidationError(
                    "'not' must contain exactly one child.")

            child = child[0]

        _validate_condition_node(child)

        return

    validate_leaf_condition(node)


def validate_leaf_condition(fragment: dict, expected_type: str | None = None) -> None:
    if not isinstance(fragment, Mapping):
        raise ConditionValidationError(
            "Condition fragment must be a JSON object.")

    condition_type = fragment.get("type")

    if condition_type not in LEAF_REQUIRED_FIELDS:
        raise ConditionValidationError(
            f"Unknown condition type: '{condition_type}'.")

    if expected_type is not None and condition_type != expected_type:
        raise ConditionValidationError(
            f"Condition fragment type '{condition_type}' does not match "
            f"condition_type '{expected_type}'."
        )

    missing_fields = [
        field for field in LEAF_REQUIRED_FIELDS[condition_type] if field not in fragment
    ]

    if missing_fields:
        raise ConditionValidationError(
            f"Missing required field(s) for {condition_type}: {', '.join(missing_fields)}."
        )

    _validate_operator(fragment, condition_type)
    _validate_type_specific_fields(fragment, condition_type)


def _validate_operator(fragment: Mapping, condition_type: str) -> None:
    op = fragment.get("op")
    if op is None:
        return

    valid_operators = TEMPORAL_OPERATORS if condition_type == "temporal" else OPERATORS
    if op not in valid_operators:
        raise ConditionValidationError(f"Unknown operator: '{op}'.")


def _validate_type_specific_fields(fragment: Mapping, condition_type: str) -> None:
    if condition_type == "membership" and not isinstance(fragment["values"], list):
        raise ConditionValidationError("Membership values must be a list.")

    if condition_type == "count":
        relationship = fragment["relationship"]

        if relationship not in EVIDENCE_TYPES:
            raise ConditionValidationError(
                f"Unknown evidence type: '{relationship}'.")

        _validate_filter(fragment.get("filter"))

    if condition_type == "aggregate":
        relationship = fragment["relationship"]
        field = fragment["field"]
        fn = fragment["fn"]

        if relationship not in AGGREGATE_RELATIONSHIPS:
            raise ConditionValidationError(
                f"Unknown aggregate relationship: '{relationship}'."
            )

        if field not in AGGREGATE_FIELDS:
            raise ConditionValidationError(
                f"Unknown aggregate field: '{field}'.")

        if fn not in AGGREGATE_FNS:
            raise ConditionValidationError(
                f"Unknown aggregate function: '{fn}'.")

        _validate_filter(fragment.get("filter"))

    if condition_type == "temporal" and fragment["op"] == "within_last":
        value = fragment["value"]

        if not isinstance(value, str) or re.fullmatch(r"\d+[dhm]", value) is None:
            raise ConditionValidationError(
                "Temporal within_last value must use '<number><d|h|m>' format."
            )


def _validate_filter(filter_spec) -> None:
    if filter_spec is None:
        return

    if not isinstance(filter_spec, Mapping):
        raise ConditionValidationError("Filter must be a JSON object.")

    unknown_keys = sorted(set(filter_spec) - EVIDENCE_FILTER_KEYS)

    if unknown_keys:
        raise ConditionValidationError(
            f"Unknown filter key(s): {', '.join(unknown_keys)}."
        )
