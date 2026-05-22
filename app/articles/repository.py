from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

COLLECTION_NAME = "articles"


class ArticleRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[COLLECTION_NAME]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index(
            [("original_url", ASCENDING)],
            unique=True,
            name="uniq_original_url",
        )
        await self.collection.create_index([("source_id", ASCENDING)], name="idx_source_id")
        await self.collection.create_index([("status", ASCENDING)], name="idx_status")
        await self.collection.create_index(
            [("crawled_at", DESCENDING)], name="idx_crawled_at_desc"
        )
        await self.collection.create_index(
            [("title", "text"), ("original_text", "text")],
            name="text_search",
        )

    async def get_by_id(self, article_id: ObjectId) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": article_id})

    async def get_by_url(self, url: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"original_url": url})

    async def create(self, data: dict[str, Any]) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        document = {
            **data,
            "crawled_at": now,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.collection.insert_one(document)
        except DuplicateKeyError:
            return None
        return await self.collection.find_one({"_id": result.inserted_id})

    async def update(
        self, article_id: ObjectId, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not data:
            return await self.get_by_id(article_id)

        data["updated_at"] = datetime.now(timezone.utc)
        return await self.collection.find_one_and_update(
            {"_id": article_id},
            {"$set": data},
            return_document=ReturnDocument.AFTER,
        )

    async def delete(self, article_id: ObjectId) -> bool:
        result = await self.collection.delete_one({"_id": article_id})
        return result.deleted_count > 0

    async def list_paginated(
        self,
        filter_query: dict[str, Any],
        page: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        total = await self.collection.count_documents(filter_query)
        cursor = (
            self.collection.find(filter_query)
            .sort("crawled_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        items = await cursor.to_list(length=limit)
        return items, total
