import time
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.articles.models import ArticleStatus
from app.articles.repository import ArticleRepository
from app.common.exceptions import NotFoundError
from app.common.logging import get_logger
from app.common.metrics import (
    crawler_articles_saved_total,
    crawler_run_duration_seconds,
    crawler_runs_total,
)
from app.crawler.fetcher import FetchError, Fetcher
from app.crawler.filters import article_passes_filters
from app.crawler.models import CrawlJobResult, CrawlStatus, CrawlTrigger
from app.crawler.parser import ParseError, Parser
from app.crawler.repository import CrawlLogRepository
from app.sources.models import Source
from app.sources.repository import SourceRepository

log = get_logger("crawler")


class CrawlerService:

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        fetcher: Fetcher,
        parser: Parser,
    ):
        self.db = db
        self.fetcher = fetcher
        self.parser = parser
        self.sources_repo = SourceRepository(db)
        self.articles_repo = ArticleRepository(db)
        self.logs_repo = CrawlLogRepository(db)

    async def run_for_source(
        self, source_id: str, trigger: CrawlTrigger = CrawlTrigger.MANUAL
    ) -> CrawlJobResult:
        if not ObjectId.is_valid(source_id):
            raise NotFoundError("Source", source_id)

        source_doc = await self.sources_repo.get_by_id(ObjectId(source_id))
        if source_doc is None:
            raise NotFoundError("Source", source_id)

        source = Source.model_validate(source_doc)
        return await self._crawl_source(source, trigger)

    async def run_all_active(self) -> list[CrawlJobResult]:
        sources_docs = await self.sources_repo.list_all()
        results: list[CrawlJobResult] = []
        for doc in sources_docs:
            source = Source.model_validate(doc)
            if not source.enabled:
                continue
            result = await self._crawl_source(source, CrawlTrigger.MANUAL)
            results.append(result)
        return results

    async def _crawl_source(
        self, source: Source, trigger: CrawlTrigger
    ) -> CrawlJobResult:
        job_id = str(uuid4())
        source_id_str = str(source.id)
        log.info("crawl_started", source_id=source_id_str, source_name=source.name, trigger=trigger.value)

        log_id = await self.logs_repo.start(ObjectId(source_id_str), trigger)
        started_at = datetime.now(timezone.utc)
        start_ts = time.perf_counter()

        found = saved = skipped = 0
        error: str | None = None
        status = CrawlStatus.SUCCESS

        try:
            index_page = await self.fetcher.fetch(source.url)
            links = self.parser.extract_article_links(source.url, index_page.html)
            links = links[: source.max_articles_per_run]
            found = len(links)
            log.info("crawl_links_found", source_id=source_id_str, count=found)

            for link in links:
                if await self.articles_repo.get_by_url(link) is not None:
                    skipped += 1
                    continue

                try:
                    page = await self.fetcher.fetch(link)
                    parsed = self.parser.parse_article(link, page.html)
                except (FetchError, ParseError) as exc:
                    log.warning("article_skipped", url=link, reason=str(exc))
                    skipped += 1
                    continue

                if not article_passes_filters(parsed, source):
                    skipped += 1
                    continue

                article_data = {
                    "source_id": ObjectId(source_id_str),
                    "original_url": parsed.url,
                    "title": parsed.title,
                    "original_text": parsed.text,
                    "rewritten_text": None,
                    "summary": None,
                    "cover_image_url": parsed.cover_image_url,
                    "topics": parsed.topics,
                    "tags": parsed.tags,
                    "author": parsed.author,
                    "published_at_source": parsed.published_at,
                    "status": ArticleStatus.NEW.value,
                    "rewrite_params": None,
                    "publish_response": None,
                }
                created = await self.articles_repo.create(article_data)
                if created is None:
                    skipped += 1
                else:
                    saved += 1
                    crawler_articles_saved_total.labels(source_id=source_id_str).inc()

            await self.sources_repo.set_last_crawled(
                ObjectId(source_id_str), datetime.now(timezone.utc)
            )

        except Exception as exc:
            status = CrawlStatus.FAILED
            error = f"{type(exc).__name__}: {exc}"
            log.exception("crawl_failed", source_id=source_id_str)

        duration = time.perf_counter() - start_ts
        crawler_run_duration_seconds.labels(source_id=source_id_str).observe(duration)
        crawler_runs_total.labels(
            source_id=source_id_str, trigger=trigger.value, status=status.value
        ).inc()

        await self.logs_repo.finish(log_id, status, found, saved, skipped, error)

        log.info(
            "crawl_finished",
            source_id=source_id_str,
            status=status.value,
            found=found,
            saved=saved,
            skipped=skipped,
            duration_s=round(duration, 2),
        )

        return CrawlJobResult(
            job_id=job_id,
            source_id=source_id_str,
            status=status,
            articles_found=found,
            articles_saved=saved,
            articles_skipped=skipped,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            error=error,
        )

    async def list_logs_for_source(self, source_id: str) -> list[dict]:
        if not ObjectId.is_valid(source_id):
            raise NotFoundError("Source", source_id)
        if await self.sources_repo.get_by_id(ObjectId(source_id)) is None:
            raise NotFoundError("Source", source_id)
        return await self.logs_repo.list_by_source(ObjectId(source_id))
