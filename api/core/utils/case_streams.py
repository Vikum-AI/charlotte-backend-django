import redis
from django.conf import settings
from django.http import Http404, StreamingHttpResponse

from api.core.models import Case


def _get_redis_client():
    return redis.Redis.from_url(settings.DRAMATIQ_BROKER["OPTIONS"]["url"])


def _decode_stream_value(value) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _stream_data(fields: dict) -> str | None:
    data = fields.get(b"data")
    if data is None:
        data = fields.get("data")
    if data is None:
        return None
    return _decode_stream_value(data)


def _sse_stream(stream_key: str):
    r = _get_redis_client()
    last_id = "$"

    while True:
        resp = r.xread({stream_key: last_id}, block=30000)
        if not resp:
            yield ": keepalive\n\n"
            continue

        for _, entries in resp:
            for entry_id, fields in entries:
                last_id = entry_id
                data = _stream_data(fields)
                if data is None:
                    continue
                yield f"data: {data}\n\n"


def case_stream_response(stream_key: str) -> StreamingHttpResponse:
    response = StreamingHttpResponse(
        _sse_stream(stream_key),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def case_graph_stream(request, case_id: str):
    del request
    if not Case.objects.filter(id=case_id).exists():
        raise Http404(f"Case '{case_id}' not found")
    return case_stream_response(f"case:{case_id}:graph")


def case_status_stream(request, case_id: str):
    del request
    if not Case.objects.filter(id=case_id).exists():
        raise Http404(f"Case '{case_id}' not found")
    return case_stream_response(f"case:{case_id}:status")
