from rest_framework.generics import CreateAPIView

from api.core.serializers import EvidenceUploadSerializer


# user uploads evidence to s3 and get link
# user sends the link to me (unconventional since we cant verify, but works for a demo)
# queue the evidence extraction pipeline


class EvidenceUploadView(CreateAPIView):
    serializer_class = EvidenceUploadSerializer
