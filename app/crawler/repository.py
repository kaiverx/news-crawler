from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.crawler.models import CrawlStatus, CrawlTrigger

COLLECTION_NAME = "crawl_logs"


class CrawlLogRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("source_id", ASCENDING), ("started_at", DESCENDING)],
            name="idx_source_started",
        )

    async def start(self, source_id: ObjectId, trigger: CrawlTrigger) -> ObjectId:
        result = await self.collection.insert_one(
            {
                "source_id": source_id,
                "started_at": datetime.now(timezone.utc),
                "finished_at": None,
                "trigger": trigger.value,
                "articles_found": 0,
                "articles_saved": 0,
                "articles_skipped": 0,
                "status": CrawlStatus.RUNNING.value,
                "error": None,
            }
        )
        return result.inserted_id

    async def finish(
        self,
        log_id: ObjectId,
        status: CrawlStatus,
        found: int,
        saved: int,
        skipped: int,
        error: str | None = None,
    ) -> None:
        await self.collection.update_one(
            {"_id": log_id},
            {
                "$set": {
                    "finished_at": datetime.now(timezone.utc),
                    "status": status.value,
                    "articles_found": found,
                    "articles_saved": saved,
                    "articles_skipped": skipped,
                    "error": error,
                }
            },
        )

    async def get_by_id(self, log_id: ObjectId) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": log_id})

    async def list_by_source(
        self, source_id: ObjectId, limit: int = 50
    ) -> list[dict[str, Any]]:
        cursor = (
            self.collection.find({"source_id": source_id})
            .sort("started_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)
