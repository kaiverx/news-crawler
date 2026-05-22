from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.common.objectid import PyObjectId


class CrawlTrigger(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class CrawlStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class CrawlLog(BaseModel):
    id: PyObjectId = Field(alias="_id")
    source_id: PyObjectId
    started_at: datetime
    finished_at: datetime | None = None
    trigger: CrawlTrigger
    articles_found: int = 0
    articles_saved: int = 0
    articles_skipped: int = 0
    status: CrawlStatus
    error: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class CrawlJobResult(BaseModel):
    job_id: str
    source_id: str
    status: CrawlStatus
    articles_found: int
    articles_saved: int
    articles_skipped: int
    started_at: datetime
    finished_at: datetime | None
    error: str | None = None


class SchedulerStatus(BaseModel):
    running: bool
    jobs_count: int
    jobs: list[dict]
