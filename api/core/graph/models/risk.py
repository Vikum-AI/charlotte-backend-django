from neomodel import (
    FloatProperty,
    IntegerProperty,
    RelationshipFrom,
    StringProperty,
)

from api.core.graph.models.base import ProofGraphNode


class RiskSignal(ProofGraphNode):
    signal_id = StringProperty(unique_index=True, required=True)
    anomaly_score = FloatProperty()
    fraud_probability = FloatProperty()
    velocity_score = FloatProperty()
    baseline_deviation = FloatProperty()

    transaction = RelationshipFrom('api.core.graph.models.financial.Transaction', 'HAS_RISK_SIGNAL')
    customer = RelationshipFrom('api.core.graph.models.financial.Customer', 'HAS_RISK_SIGNAL')
    case = RelationshipFrom('api.core.graph.models.investigation.Case', 'HAS_RISK_SIGNAL')


class CustomerBehaviourProfile(ProofGraphNode):
    profile_id = StringProperty(unique_index=True, required=True)
    avg_transaction = FloatProperty()
    max_transaction = FloatProperty()
    transactions_30d = IntegerProperty()
    country_diversity_score = FloatProperty()

    customer = RelationshipFrom('api.core.graph.models.financial.Customer', 'HAS_PROFILE')
