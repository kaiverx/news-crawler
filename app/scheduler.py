from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.crawler.dependencies import get_fetcher, get_parser
from app.crawler.models import CrawlTrigger
from app.crawler.service import CrawlerService
from app.sources.models import Source
from app.sources.repository import SourceRepository


class SchedulerManager:
    scheduler: AsyncIOScheduler | None = None
    db: AsyncIOMotorDatabase | None = None


manager = SchedulerManager()


async def _run_crawl_job(source_id: str) -> None:
    if manager.db is None:
        return
    service = CrawlerService(manager.db, get_fetcher(), get_parser())
    await service.run_for_source(source_id, trigger=CrawlTrigger.SCHEDULED)


async def init_scheduler(db: AsyncIOMotorDatabase) -> None:
    manager.db = db
    manager.scheduler = AsyncIOScheduler(timezone="UTC")
    manager.scheduler.start()
    await reload_jobs()


async def shutdown_scheduler() -> None:
    if manager.scheduler is not None:
        manager.scheduler.shutdown(wait=True)


async def reload_jobs() -> None:
    if manager.scheduler is None or manager.db is None:
        return

    for job in manager.scheduler.get_jobs():
        job.remove()

    repo = SourceRepository(manager.db)
    docs = await repo.list_all()
    for doc in docs:
        source = Source.model_validate(doc)
        if not source.enabled:
            continue
        try:
            trigger = CronTrigger.from_crontab(source.schedule, timezone="UTC")
        except ValueError:
            continue
        manager.scheduler.add_job(
            _run_crawl_job,
            trigger=trigger,
            args=[str(source.id)],
            id=f"crawl_{source.id}",
            replace_existing=True,
            misfire_grace_time=300,
        )


def get_scheduler() -> AsyncIOScheduler:
    if manager.scheduler is None:
        raise RuntimeError("Планировщик не инициализирован")
    return manager.scheduler
