from neomodel import (
    BooleanProperty,
    DateTimeProperty,
    FloatProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
)

from api.core.graph.base import ProofGraphNode


class Employee(ProofGraphNode):
    employee_id = StringProperty(unique_index=True, required=True)
    name = StringProperty()
    role = StringProperty()
    department = StringProperty()

    approves = RelationshipTo('Approval', 'APPROVES')


class Approval(ProofGraphNode):
    approval_id = StringProperty(unique_index=True, required=True)
    timestamp = DateTimeProperty()
    decision = StringProperty()
    method = StringProperty()

    approver = RelationshipFrom('Employee', 'APPROVES')
    for_transaction = RelationshipTo('Transaction', 'FOR')
    supported_by = RelationshipFrom('Evidence', 'SUPPORTS')


class AMLCheck(ProofGraphNode):
    check_id = StringProperty(unique_index=True, required=True)
    provider = StringProperty()
    result = StringProperty()
    confidence = FloatProperty()
    timestamp = DateTimeProperty()

    screens = RelationshipFrom('Transaction', 'SCREENED_BY')
    supported_by = RelationshipFrom('Evidence', 'SUPPORTS')


class Country(ProofGraphNode):
    country_code = StringProperty(unique_index=True, required=True)
    risk_level = StringProperty()
    sanctions_flag = BooleanProperty(default=False)

    customers = RelationshipFrom('Customer', 'LOCATED_IN')
    destination_transactions = RelationshipFrom(
        'Transaction', 'DESTINATION_COUNTRY')
