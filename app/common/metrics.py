import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

crawler_runs_total = Counter(
    "crawler_runs_total",
    "Количество запусков обхода",
    ["source_id", "trigger", "status"],
)

crawler_articles_saved_total = Counter(
    "crawler_articles_saved_total",
    "Количество сохранённых статей",
    ["source_id"],
)

crawler_run_duration_seconds = Histogram(
    "crawler_run_duration_seconds",
    "Длительность обхода источника",
    ["source_id"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "Длительность HTTP-запросов",
    ["method", "path", "status_code"],
)

llm_rewrite_duration_seconds = Histogram(
    "llm_rewrite_duration_seconds",
    "Длительность LLM-рерайта",
    ["provider", "status"],
)


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start
            path_template = request.scope.get("route").path if request.scope.get("route") else request.url.path
            api_request_duration_seconds.labels(
                method=request.method,
                path=path_template,
                status_code=status_code,
            ).observe(duration)
        return response
