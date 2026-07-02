from neomodel import (
    BooleanProperty,
    DateTimeProperty,
    FloatProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
)

from api.core.graph.models.base import ProofGraphNode


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
    for_transaction = RelationshipTo('api.core.graph.models.financial.Transaction', 'FOR')
    supported_by = RelationshipFrom('api.core.graph.models.investigation.Evidence', 'SUPPORTS')


class AMLCheck(ProofGraphNode):
    check_id = StringProperty(unique_index=True, required=True)
    provider = StringProperty()
    result = StringProperty()
    confidence = FloatProperty()
    timestamp = DateTimeProperty()

    screens = RelationshipFrom('api.core.graph.models.financial.Transaction', 'SCREENED_BY')
    supported_by = RelationshipFrom('api.core.graph.models.investigation.Evidence', 'SUPPORTS')


class Country(ProofGraphNode):
    country_code = StringProperty(unique_index=True, required=True)
    risk_level = StringProperty()
    sanctions_flag = BooleanProperty(default=False)

    customers = RelationshipFrom('api.core.graph.models.financial.Customer', 'LOCATED_IN')
    destination_transactions = RelationshipFrom(
        'api.core.graph.models.financial.Transaction', 'DESTINATION_COUNTRY')
