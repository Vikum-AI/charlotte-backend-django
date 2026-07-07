from rest_framework import status
from rest_framework.response import Response


def processing_response() -> Response:
    return Response({"status": "processing"}, status=status.HTTP_202_ACCEPTED)
