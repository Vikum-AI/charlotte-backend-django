from neomodel import db

from api.core.evidence.results import ResolutionResult
from api.user_management.models import User, UserRole

MATCHED = 'MATCHED'
MISMATCH = 'MISMATCH'
UNRESOLVED = 'UNRESOLVED'

TRANSACTION_PROPERTIES = frozenset({
    'amount', 'currency', 'status', 'channel', 'category', 'type', 'step',
})
CUSTOMER_PROPERTIES = frozenset({
    'kyc_status', 'risk_rating', 'industry', 'name',
})

CUSTOMER_KYC_QUERY = """
MATCH (c:Customer {customer_id: $customer_id})
RETURN c.kyc_status AS value
"""

TRANSACTION_PROPERTY_QUERY = """
MATCH (t:Transaction {transaction_id: $transaction_id})
RETURN t[$property] AS value
"""

CUSTOMER_PROPERTY_QUERY = """
MATCH (c:Customer)-[:OWNS]->(:Account)-[:INITIATES]->(t:Transaction {transaction_id: $transaction_id})
RETURN c[$property] AS value
LIMIT 1
"""

DESTINATION_COUNTRY_QUERY = """
MATCH (t:Transaction {transaction_id: $transaction_id})-[:DESTINATION_COUNTRY]->(co:Country)
RETURN co.country_code AS value
"""


def resolve_approval(
    transaction_id: str,
    approver_email: str | None,
    approval_date: str | None,
) -> ResolutionResult:
    del transaction_id

    if approver_email is None:
        return ResolutionResult(
            status=UNRESOLVED,
            reason='No approver email extracted',
        )

    user = User.objects.filter(email__iexact=approver_email).first()
    if user is None:
        return ResolutionResult(
            status=UNRESOLVED,
            reason=f"'{approver_email}' not found in authorized approvers list",
        )

    if user.role in (UserRole.VIEWER, UserRole.RESTRICTED):
        return ResolutionResult(
            status=UNRESOLVED,
            reason=(
                f"'{approver_email}' found but not authorized to approve "
                f"(role: {user.get_role_display()})"
            ),
        )

    if user.role in (UserRole.ADMIN, UserRole.EDITOR):
        return ResolutionResult(
            status=MATCHED,
            resolved_payload={
                'approver_email': approver_email,
                'approval_date': approval_date,
                'role': user.get_role_display(),
                'user_id': str(user.id),
            },
        )

    return ResolutionResult(
        status=UNRESOLVED,
        reason=f"'{approver_email}' has unrecognized role for approval",
    )


def resolve_kyc_status(
    customer_id: str,
    kyc_status_value: str | None,
    verification_date: str | None,
) -> ResolutionResult:
    if kyc_status_value is None:
        return ResolutionResult(
            status=UNRESOLVED,
            reason='No KYC status extracted',
        )

    graph_value = _fetch_customer_kyc_status(customer_id)
    payload = {
        'kyc_status_value': kyc_status_value,
        'verification_date': verification_date,
        'customer_id': customer_id,
    }

    if graph_value is None:
        return ResolutionResult(status=MATCHED, resolved_payload=payload)

    if str(graph_value).lower() != str(kyc_status_value).lower():
        return ResolutionResult(
            status=MISMATCH,
            reason='Extracted value contradicts existing graph value',
            resolved_payload={
                **payload,
                'graph_value': graph_value,
            },
        )

    return ResolutionResult(status=MATCHED, resolved_payload=payload)


def resolve_field_path(
    field_path: str,
    transaction_id: str,
    customer_id: str | None = None,
):
    del customer_id

    if field_path == 'transaction.destination_country':
        return _fetch_destination_country(transaction_id)

    if '.' not in field_path:
        return None

    node_type, property_name = field_path.split('.', 1)

    if node_type == 'transaction' and property_name in TRANSACTION_PROPERTIES:
        return _fetch_transaction_property(transaction_id, property_name)

    if node_type == 'customer' and property_name in CUSTOMER_PROPERTIES:
        return _fetch_customer_property_via_transaction(transaction_id, property_name)

    return None


def resolve_custom(
    field_path: str,
    extracted_value: str,
    transaction_id: str,
    customer_id: str | None = None,
) -> ResolutionResult:
    if not _is_known_field_path(field_path):
        return ResolutionResult(
            status=UNRESOLVED,
            reason='Unknown field path',
        )

    graph_value = resolve_field_path(field_path, transaction_id, customer_id)
    payload = {
        'field_path': field_path,
        'extracted_value': extracted_value,
        'transaction_id': transaction_id,
    }
    if customer_id is not None:
        payload['customer_id'] = customer_id

    if graph_value is None:
        return ResolutionResult(status=MATCHED, resolved_payload=payload)

    if str(graph_value).lower() != str(extracted_value).lower():
        return ResolutionResult(
            status=MISMATCH,
            reason='Extracted value contradicts existing graph value',
            resolved_payload={
                **payload,
                'graph_value': graph_value,
            },
        )

    return ResolutionResult(status=MATCHED, resolved_payload=payload)


def _is_known_field_path(field_path: str) -> bool:
    if field_path == 'transaction.destination_country':
        return True
    if '.' not in field_path:
        return False
    node_type, property_name = field_path.split('.', 1)
    if node_type == 'transaction':
        return property_name in TRANSACTION_PROPERTIES
    if node_type == 'customer':
        return property_name in CUSTOMER_PROPERTIES
    return False


def _fetch_customer_kyc_status(customer_id: str):
    results, _ = db.cypher_query(
        CUSTOMER_KYC_QUERY,
        {'customer_id': customer_id},
    )
    if not results:
        return None
    return results[0][0]


def _fetch_transaction_property(transaction_id: str, property_name: str):
    results, _ = db.cypher_query(
        TRANSACTION_PROPERTY_QUERY,
        {'transaction_id': transaction_id, 'property': property_name},
    )
    if not results:
        return None
    return results[0][0]


def _fetch_customer_property_via_transaction(transaction_id: str, property_name: str):
    results, _ = db.cypher_query(
        CUSTOMER_PROPERTY_QUERY,
        {'transaction_id': transaction_id, 'property': property_name},
    )
    if not results:
        return None
    return results[0][0]


def _fetch_destination_country(transaction_id: str):
    results, _ = db.cypher_query(
        DESTINATION_COUNTRY_QUERY,
        {'transaction_id': transaction_id},
    )
    if not results:
        return None
    return results[0][0]
