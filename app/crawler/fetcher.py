import asyncio
from dataclasses import dataclass

import httpx

USER_AGENT = (
    "Mozilla/5.0 (compatible; NewsCrawlerBot/0.1; +https://example.com/bot)"
)
DEFAULT_TIMEOUT = 20.0
MAX_RETRIES = 3
BACKOFF_BASE = 1.0


class FetchError(Exception):
    pass


@dataclass
class FetchedPage:
    url: str
    final_url: str
    status_code: int
    html: str


class Fetcher:

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, max_concurrent: int = 10):
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            limits=httpx.Limits(max_connections=max_concurrent),
        )
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch(self, url: str) -> FetchedPage:
        async with self._semaphore:
            return await self._fetch_with_retry(url)

    async def _fetch_with_retry(self, url: str) -> FetchedPage:
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                return FetchedPage(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    html=response.text,
                )
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
        raise FetchError(f"Не удалось загрузить {url} после {MAX_RETRIES} попыток: {last_exc}")
