from neomodel import (
    ArrayProperty,
    DateTimeProperty,
    FloatProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
)

from api.core.graph.base import ProofGraphNode


class Customer(ProofGraphNode):
    customer_id = StringProperty(unique_index=True, required=True)
    name = StringProperty()
    risk_rating = StringProperty()
    kyc_status = StringProperty()
    industry = StringProperty()

    accounts = RelationshipTo('Account', 'OWNS')
    located_in = RelationshipTo('Country', 'LOCATED_IN')
    behaviour_profile = RelationshipTo(
        'CustomerBehaviourProfile', 'HAS_PROFILE')
    risk_signals = RelationshipTo('RiskSignal', 'HAS_RISK_SIGNAL')


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
    amount = FloatProperty()
    currency = StringProperty()
    timestamp = DateTimeProperty()
    status = StringProperty()
    channel = StringProperty()
    category = StringProperty()
    step = StringProperty()
    type = StringProperty()
    synthetic_fields = ArrayProperty(StringProperty(), default=list)

    initiated_by_account = RelationshipFrom('Account', 'INITIATES')
    screened_by = RelationshipTo('AMLCheck', 'SCREENED_BY')
    destination_country = RelationshipTo('Country', 'DESTINATION_COUNTRY')
    risk_signals = RelationshipTo('RiskSignal', 'HAS_RISK_SIGNAL')
    approvals = RelationshipFrom('Approval', 'FOR')
    investigated_by = RelationshipFrom('Case', 'INVESTIGATES')
    supported_by = RelationshipFrom('Evidence', 'SUPPORTS')
