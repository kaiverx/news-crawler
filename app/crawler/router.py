from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.common.exceptions import NotFoundError
from app.crawler.dependencies import get_fetcher, get_parser
from app.crawler.fetcher import Fetcher
from app.crawler.models import CrawlJobResult, CrawlLog, SchedulerStatus
from app.crawler.parser import Parser
from app.crawler.service import CrawlerService
from app.database import get_db
from app.scheduler import get_scheduler

router = APIRouter(prefix="/crawler", tags=["crawler"])


def get_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    fetcher: Fetcher = Depends(get_fetcher),
    parser: Parser = Depends(get_parser),
) -> CrawlerService:
    return CrawlerService(db, fetcher, parser)


@router.post("/run", summary="Запустить обход всех активных источников")
async def run_all(
    background: BackgroundTasks,
    service: CrawlerService = Depends(get_service),
) -> dict:
    background.add_task(service.run_all_active)
    return {"status": "scheduled", "message": "Обход всех активных источников запущен в фоне"}


@router.post(
    "/run/{source_id}",
    response_model=CrawlJobResult,
    summary="Запустить обход конкретного источника",
)
async def run_one(
    source_id: str,
    service: CrawlerService = Depends(get_service),
) -> CrawlJobResult:
    try:
        return await service.run_for_source(source_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/status", response_model=SchedulerStatus, summary="Статус планировщика")
async def scheduler_status() -> SchedulerStatus:
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
        )
    return SchedulerStatus(
        running=scheduler.running,
        jobs_count=len(jobs),
        jobs=jobs,
    )


@router.get(
    "/sources/{source_id}/logs",
    response_model=list[CrawlLog],
    summary="История обходов источника",
)
async def list_source_logs(
    source_id: str,
    service: CrawlerService = Depends(get_service),
) -> list[CrawlLog]:
    try:
        docs = await service.list_logs_for_source(source_id)
        return [CrawlLog.model_validate(d) for d in docs]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
