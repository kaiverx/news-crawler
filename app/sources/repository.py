from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

COLLECTION_NAME = "sources"


class SourceRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db[COLLECTION_NAME]

    async def list_all(self) -> list[dict[str, Any]]:
        cursor = self.collection.find().sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def get_by_id(self, source_id: ObjectId) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": source_id})

    async def get_by_url(self, url: str) -> dict[str, Any] | None:

        return await self.collection.find_one({"url": url})

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        document = {
            **data,
            "created_at": now,
            "updated_at": now,
            "last_crawled_at": None,
        }
        result = await self.collection.insert_one(document)
        return await self.collection.find_one({"_id": result.inserted_id})  

    async def update(self, source_id: ObjectId, data: dict[str, Any]) -> dict[str, Any] | None:

        from pymongo import ReturnDocument

        if not data:
            return await self.get_by_id(source_id)

        data["updated_at"] = datetime.now(timezone.utc)
        return await self.collection.find_one_and_update(
            {"_id": source_id},
            {"$set": data},
            return_document=ReturnDocument.AFTER,
        )

    async def delete(self, source_id: ObjectId) -> bool:
        """Удаляет документ. Возвращает True, если что-то реально удалилось."""
        result = await self.collection.delete_one({"_id": source_id})
        return result.deleted_count > 0

    async def set_last_crawled(self, source_id: ObjectId, when: datetime) -> None:
        """
        Обновляет только поле last_crawled_at.
        Пригодится Crawler-модулю в следующем спринте.
        """
        await self.collection.update_one(
            {"_id": source_id},
            {"$set": {"last_crawled_at": when, "updated_at": datetime.now(timezone.utc)}},
        )
