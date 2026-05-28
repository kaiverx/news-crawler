from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings

PUBLIC_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json", "/metrics"}


class ApiKeyMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        if not settings.api_key:
            return await call_next(request)

        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        provided = request.headers.get("X-API-Key")
        if provided != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный или отсутствующий X-API-Key",
            )

        return await call_next(request)
