from neomodel import (
    DateTimeProperty,
    FloatProperty,
    JSONProperty,
    RelationshipFrom,
    RelationshipTo,
    StringProperty,
)

from api.core.graph.base import ProofGraphNode


class Case(ProofGraphNode):
    case_id = StringProperty(unique_index=True, required=True)
    status = StringProperty()
    created_at = DateTimeProperty()

    investigates = RelationshipTo('Transaction', 'INVESTIGATES')
    evidence = RelationshipTo('Evidence', 'HAS_EVIDENCE')
    evaluations = RelationshipTo('RuleEvaluation', 'HAS_EVALUATION')
    risk_signals = RelationshipTo('RiskSignal', 'HAS_RISK_SIGNAL')
    supported_by = RelationshipFrom('Evidence', 'SUPPORTS')


class Evidence(ProofGraphNode):
    evidence_id = StringProperty(unique_index=True, required=True)
    evidence_type = StringProperty(required=True)
    extracted_at = DateTimeProperty()
    confidence = FloatProperty()
    source_document_id = StringProperty()
    file_key = StringProperty()
    source_text = StringProperty()
    source_start_offset = FloatProperty()
    source_end_offset = FloatProperty()
    raw_extraction = JSONProperty()
    resolved_status = StringProperty()
    resolution_reason = StringProperty()
    payload = JSONProperty()

    case = RelationshipFrom('Case', 'HAS_EVIDENCE')
    supports = RelationshipTo('Transaction', 'SUPPORTS')
    supports_approval = RelationshipTo('Approval', 'SUPPORTS')
    supports_aml_check = RelationshipTo('AMLCheck', 'SUPPORTS')
    supports_case = RelationshipTo('Case', 'SUPPORTS')


class Rule(ProofGraphNode):
    rule_id = StringProperty(unique_index=True, required=True)
    name = StringProperty()
    type = StringProperty()
    yaml_definition = StringProperty()

    evaluations = RelationshipFrom('RuleEvaluation', 'EVALUATES')


class RuleEvaluation(ProofGraphNode):
    evaluation_id = StringProperty(unique_index=True, required=True)
    status = StringProperty()
    score = FloatProperty()
    evaluated_at = DateTimeProperty()

    case = RelationshipFrom('Case', 'HAS_EVALUATION')
    rule = RelationshipTo('Rule', 'EVALUATES')
