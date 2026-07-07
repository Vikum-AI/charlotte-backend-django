import uuid

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from neomodel import db

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet

from api.core.models import Case, CaseRule, SuggestedEvidence, SuggestedSubRule
from api.core.serializers import (
    AddSuggestedEvidenceSerializer,
    CaseCreateSerializer,
    CaseDetailResponseSerializer,
    CaseRuleCreateSerializer,
    ConfirmEvidenceSerializer,
    EvidenceUploadSerializer,
    SuggestedEvidenceResponseSerializer,
    SuggestedSubRuleResponseSerializer,
)
from api.core.tasks.evidence_extraction_tasks import extract_data_from_evidence
from api.core.utils.cases import serialize_case_list_item, serialize_case_rule
from api.core.utils.evidence.case_scope import attach_evidence, detach_evidence
from api.core.utils.evidence.confirm import confirm_provisional_evidence
from api.core.utils.evidence.exceptions import EvidenceConfirmationError
from api.core.utils.evidence.queries import get_existing_evidence_or_404
from api.core.utils.graph_events import publish_evidence_created
from api.core.utils.graph_snapshot import get_case_graph_snapshot
from api.core.utils.responses import processing_response
from api.core.utils.suggested_evidence import (
    already_added_suggested_evidence_ids,
    is_suggested_evidence_applicable,
    suggested_evidence_metadata,
)
from api.core.utils.suggested_subrules import is_suggested_sub_rule_applicable
from api.core.utils.transactions import (
    transaction_exists,
    transaction_ids_matching_case_search,
)


# user uploads evidence to s3 and get link
# user sends the link to me (unconventional since we cant verify, but works for a demo)
# queue the evidence extraction pipeline


class EvidenceUploadViewSet(GenericViewSet):
    serializer_class = EvidenceUploadSerializer

    def create(self, request, case_id=None, *args, **kwargs):
        data = request.data.copy()
        
        if case_id is not None:
            body_case_id = data.get("case_id")
            
            if body_case_id and body_case_id != case_id:
                return Response(
                    {"case_id": "Body case_id does not match the URL case_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            data["case_id"] = case_id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        
        get_object_or_404(Case, id=serializer.validated_data["case_id"])
        
        serializer.save()
        return processing_response()


class CaseCreateViewSet(GenericViewSet):
    serializer_class = CaseCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction_id = serializer.validated_data["transaction_id"]

        if not transaction_exists(transaction_id):
            return Response(
                {"transaction_id": f"Transaction '{transaction_id}' was not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        case = Case.objects.create(
            id=str(uuid.uuid4()),
            transaction_id=transaction_id,
            status="open",
            assigned_to=serializer.validated_data.get("assigned_to") or None,
        )
        
        return Response(
            {
                "id": case.id,
                "transaction_id": case.transaction_id,
                "status": case.status,
            },
            status=status.HTTP_201_CREATED,
        )


class TransactionSearchViewSet(ViewSet):
    def list(self, request):
        q = request.query_params.get("q", "").strip()
        limit = min(int(request.query_params.get("limit", 20)), 50)

        cypher = """
        MATCH (t:Transaction {is_demo_featured: true})
        OPTIONAL MATCH (c:Customer)-[:OWNS]->(:Account)-[:INITIATES]->(t)
        WITH t, c
        WHERE $q = ""
           OR toLower(t.transaction_id) CONTAINS toLower($q)
           OR toString(t.amount) CONTAINS $q
           OR toLower(t.channel) CONTAINS toLower($q)
           OR toLower(coalesce(c.customer_id, "")) CONTAINS toLower($q)
        RETURN t.transaction_id AS transaction_id, t.amount AS amount,
               t.currency AS currency, t.channel AS channel, t.status AS status,
               c.customer_id AS customer_id, c.name AS customer_name
        ORDER BY t.transaction_id
        LIMIT $limit
        """
        
        results, _ = db.cypher_query(cypher, {"q": q, "limit": limit})
        transaction_ids = [row[0] for row in results]
        existing_case_ids = dict(
            Case.objects.filter(transaction_id__in=transaction_ids).values_list(
                "transaction_id",
                "id",
            ),
        )
        
        return Response(
            [
                {
                    "transaction_id": row[0],
                    "amount": row[1],
                    "currency": row[2],
                    "channel": row[3],
                    "status": row[4],
                    "customer_id": row[5],
                    "customer_name": row[6],
                    "existing_case_id": existing_case_ids.get(row[0]),
                }
                for row in results
            ],
        )


class CaseDetailViewSet(GenericViewSet):
    serializer_class = CaseDetailResponseSerializer

    def list(self, request, *args, **kwargs):
        del args, kwargs
        
        q = request.query_params.get("q", "").strip()
        cases = Case.objects.order_by("-created_at")
        
        if q:
            transaction_ids = transaction_ids_matching_case_search(q)
            cases = cases.filter(
                Q(id__icontains=q) | Q(transaction_id__in=transaction_ids),
            ).distinct()
        
        return Response([serialize_case_list_item(case) for case in cases])

    def retrieve(self, request, case_id=None, *args, **kwargs):
        del request, args, kwargs
        
        case_id = case_id or self.kwargs.get("pk")
        case = get_object_or_404(Case, id=case_id)
        rules = CaseRule.objects.filter(case=case).select_related("evaluation")
        
        return Response(
            {
                "case": {
                    "id": case.id,
                    "status": case.status,
                    "transaction_id": case.transaction_id,
                },
                "graph": get_case_graph_snapshot(case_id),
                "rules": [serialize_case_rule(rule) for rule in rules],
            }
        )


class CaseViewSet(CaseCreateViewSet, CaseDetailViewSet):
    lookup_url_kwarg = "case_id"
    queryset = Case.objects.all()


class CaseRuleViewSet(GenericViewSet):
    serializer_class = CaseRuleCreateSerializer

    def create(self, request, case_id, *args, **kwargs):
        del args, kwargs
        case = get_object_or_404(Case, id=case_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case_rule = CaseRule.objects.create(
            case=case,
            rule_id=serializer.validated_data["rule_id"],
            definition=serializer.validated_data["definition"],
        )
        
        return Response(
            {"id": case_rule.id, "rule_id": case_rule.rule_id},
            status=status.HTTP_201_CREATED,
        )


class SuggestedEvidenceViewSet(GenericViewSet):
    serializer_class = SuggestedEvidenceResponseSerializer

    def list(self, request, case_id, *args, **kwargs):
        del request, args, kwargs
        
        case = get_object_or_404(Case, id=case_id)
        items = [
            item
            for item in SuggestedEvidence.objects.filter(is_active=True)
            if is_suggested_evidence_applicable(item, case)
        ]
        
        already_added_ids = already_added_suggested_evidence_ids(case, items)

        return Response(
            [
                {
                    "id": item.id,
                    "label": item.label,
                    "description": item.description,
                    "evidence_type": item.evidence_type,
                    "file_url": item.file_url,
                    "field_path": item.field_path,
                    "suggested_condition": item.suggested_condition,
                    "already_added": item.id in already_added_ids,
                }
                for item in items
            ]
        )


class SuggestedSubRuleViewSet(GenericViewSet):
    serializer_class = SuggestedSubRuleResponseSerializer

    def list(self, request, case_id, *args, **kwargs):
        del request, args, kwargs
        
        case = get_object_or_404(Case, id=case_id)
        items = [
            item
            for item in SuggestedSubRule.objects.filter(is_active=True)
            if is_suggested_sub_rule_applicable(item, case)
        ]

        return Response(
            [
                {
                    "id": item.id,
                    "label": item.label,
                    "description": item.description,
                    "tier": item.tier,
                    "condition_type": item.condition_type,
                    "condition_fragment": item.condition_fragment,
                }
                for item in items
            ]
        )


class AddSuggestedEvidenceViewSet(GenericViewSet):
    serializer_class = AddSuggestedEvidenceSerializer

    def create(self, request, case_id, *args, **kwargs):
        del args, kwargs
        
        case = get_object_or_404(Case, id=case_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggested = get_object_or_404(
            SuggestedEvidence,
            id=serializer.validated_data["suggested_evidence_id"],
            is_active=True,
        )
        
        if not is_suggested_evidence_applicable(suggested, case):
            raise Http404(f"Suggested evidence '{suggested.id}' not found")

        if suggested.evidence_type == SuggestedEvidence.EvidenceType.CUSTOM:
            if not suggested.field_path or suggested.extracted_value is None:
                return Response(
                    {
                        "detail": (
                            "Custom suggested evidence requires field_path and extracted_value."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        extract_data_from_evidence.send(
            case.id,
            suggested.file_url,
            suggested_evidence_metadata(suggested),
        )
        
        return processing_response()


class EvidenceAttachViewSet(ViewSet):
    def create(self, request, case_id=None, evidence_id=None):
        del request
        
        case = get_object_or_404(Case, id=case_id)
        evidence = get_existing_evidence_or_404(evidence_id)
        evidence_case_id = evidence.get("case_id")
        
        if evidence_case_id and evidence_case_id != case_id:
            return Response(
                {"detail": "Evidence belongs to another case."},
                status=status.HTTP_409_CONFLICT,
            )
        attached = attach_evidence(case_id, evidence_id)
        
        if attached:
            publish_evidence_created(case_id, case.transaction_id, evidence)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class EvidenceDetachViewSet(ViewSet):
    def create(self, request, case_id=None, evidence_id=None):
        del request
        
        get_object_or_404(Case, id=case_id)
        get_existing_evidence_or_404(evidence_id)
        detach_evidence(case_id, evidence_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfirmEvidenceViewSet(ViewSet):
    def create(self, request, evidence_id=None):
        serializer = ConfirmEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            confirm_provisional_evidence(
                evidence_id,
                serializer.validated_data["confirmed_by_user_id"],
            )
        except EvidenceConfirmationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# for backwards comp (cleanup later)
EvidenceUploadView = EvidenceUploadViewSet
CaseCreateView = CaseCreateViewSet
TransactionSearchView = TransactionSearchViewSet
CaseDetailView = CaseDetailViewSet
CaseRuleCreateView = CaseRuleViewSet
SuggestedEvidenceListView = SuggestedEvidenceViewSet
SuggestedSubRuleListView = SuggestedSubRuleViewSet
AddSuggestedEvidenceView = AddSuggestedEvidenceViewSet
EvidenceAttachView = EvidenceAttachViewSet
EvidenceDetachView = EvidenceDetachViewSet
ConfirmEvidenceView = ConfirmEvidenceViewSet
