from neomodel import (
    ArrayProperty,
    BooleanProperty,
    DateTimeNeo4jFormatProperty,
    FloatProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
)

from api.core.graph.models.base import ProofGraphNode


class Customer(ProofGraphNode):
    customer_id = StringProperty(unique_index=True, required=True)
    name = StringProperty()
    risk_rating = StringProperty()
    kyc_status = StringProperty()
    industry = StringProperty()

    accounts = RelationshipTo('Account', 'OWNS')
    located_in = RelationshipTo('api.core.graph.models.compliance.Country', 'LOCATED_IN')
    behaviour_profile = RelationshipTo(
        'api.core.graph.models.risk.CustomerBehaviourProfile', 'HAS_PROFILE')
    risk_signals = RelationshipTo(
        'api.core.graph.models.risk.RiskSignal', 'HAS_RISK_SIGNAL')


class Account(ProofGraphNode):
    account_id = StringProperty(unique_index=True, required=True)
    type = StringProperty()
    currency = StringProperty()
    status = StringProperty()
    role = StringProperty(choices=(
        ('source', 'source'),
        ('counterparty', 'counterparty'),
    ))

    owner = RelationshipFrom('Customer', 'OWNS')
    initiates = RelationshipTo('Transaction', 'INITIATES')


class Transaction(ProofGraphNode):
    transaction_id = StringProperty(unique_index=True, required=True)
    is_demo_featured = BooleanProperty(default=False)
    amount = FloatProperty()
    currency = StringProperty()
    timestamp = DateTimeNeo4jFormatProperty()
    status = StringProperty()
    channel = StringProperty()
    category = StringProperty()
    step = StringProperty()
    type = StringProperty()
    synthetic_fields = ArrayProperty(StringProperty(), default=list)

    initiated_by_account = RelationshipFrom('Account', 'INITIATES')
    screened_by = RelationshipTo('api.core.graph.models.compliance.AMLCheck', 'SCREENED_BY')
    destination_country = RelationshipTo(
        'api.core.graph.models.compliance.Country', 'DESTINATION_COUNTRY')
    risk_signals = RelationshipTo(
        'api.core.graph.models.risk.RiskSignal', 'HAS_RISK_SIGNAL')
    approvals = RelationshipFrom('api.core.graph.models.compliance.Approval', 'FOR')
    investigated_by = RelationshipFrom('api.core.graph.models.investigation.Case', 'INVESTIGATES')
    supported_by = RelationshipFrom('api.core.graph.models.investigation.Evidence', 'SUPPORTS')
