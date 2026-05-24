import asyncio
from typing import Any

import httpx


class PublishError(Exception):
    pass


class ArticlePublisher:

    def __init__(self, main_service_url: str, timeout: float = 30.0):
        self.main_service_url = main_service_url
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.main_service_url:
            raise PublishError("MAIN_SERVICE_URL не настроен")

        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = await self._client.post(self.main_service_url, json=payload)
                response.raise_for_status()
                try:
                    body = response.json()
                except ValueError:
                    body = {"raw": response.text}
                return {"status_code": response.status_code, "body": body}
            except httpx.HTTPStatusError as exc:
                if 400 <= exc.response.status_code < 500:
                    raise PublishError(
                        f"Основной сервис вернул {exc.response.status_code}: {exc.response.text}"
                    )
                last_exc = exc
            except httpx.HTTPError as exc:
                last_exc = exc
            if attempt < 3:
                await asyncio.sleep(2 ** (attempt - 1))

        raise PublishError(f"Не удалось опубликовать после 3 попыток: {last_exc}")
