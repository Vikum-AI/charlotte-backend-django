from django.urls import include, path
from rest_framework.routers import APIRootView, DefaultRouter

from api.core.utils.case_streams import case_graph_stream, case_status_stream
from api.core.views import (
    AddSuggestedEvidenceViewSet,
    CaseRuleViewSet,
    CaseViewSet,
    ConfirmEvidenceViewSet,
    EvidenceAttachViewSet,
    EvidenceDetachViewSet,
    EvidenceUploadViewSet,
    SuggestedEvidenceViewSet,
    SuggestedSubRuleViewSet,
    TransactionSearchViewSet,
)


class CoreRootView(APIRootView):
    ...


router = DefaultRouter()
router.APIRootView = CoreRootView
router.trailing_slash = "/?"

router.register("transactions", TransactionSearchViewSet,
                basename="transaction-search")
router.register("cases", CaseViewSet, basename="case")
router.register(
    r"cases/(?P<case_id>[^/.]+)/rules",
    CaseRuleViewSet,
    basename="case-rule",
)
router.register(
    r"cases/(?P<case_id>[^/.]+)/suggested-evidence",
    SuggestedEvidenceViewSet,
    basename="suggested-evidence",
)
router.register(
    r"cases/(?P<case_id>[^/.]+)/suggested-subrules",
    SuggestedSubRuleViewSet,
    basename="suggested-subrules",
)
router.register(
    r"cases/(?P<case_id>[^/.]+)/evidence/suggested",
    AddSuggestedEvidenceViewSet,
    basename="add-suggested-evidence",
)
router.register(
    r"cases/(?P<case_id>[^/.]+)/evidence/upload",
    EvidenceUploadViewSet,
    basename="evidence-upload",
)
router.register(
    r"cases/(?P<case_id>[^/.]+)/evidence/(?P<evidence_id>[^/.]+)/attach",
    EvidenceAttachViewSet,
    basename="evidence-attach",
)
router.register(
    r"cases/(?P<case_id>[^/.]+)/evidence/(?P<evidence_id>[^/.]+)/detach",
    EvidenceDetachViewSet,
    basename="evidence-detach",
)
router.register(
    r"evidence/(?P<evidence_id>[^/.]+)/confirm",
    ConfirmEvidenceViewSet,
    basename="evidence-confirm",
)


urlpatterns = [
    path("", include(router.urls)),
    path(
        "cases/<str:case_id>/events/graph",
        case_graph_stream,
        name="case-graph-stream",
    ),
    path("cases/<str:case_id>/events/graph/", case_graph_stream),
    path(
        "cases/<str:case_id>/events/status",
        case_status_stream,
        name="case-status-stream",
    ),
    path("cases/<str:case_id>/events/status/", case_status_stream),
    path("cases", CaseViewSet.as_view({"post": "create"}), name="case-create"),
    path(
        "cases/<str:case_id>/evidence/upload",
        EvidenceUploadViewSet.as_view({"post": "create"}),
        name="evidence-upload",
    ),
    path(
        "transactions/",
        TransactionSearchViewSet.as_view({"get": "list"}),
        name="transaction-search",
    ),
]
