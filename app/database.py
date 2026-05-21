
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings


class MongoDB:

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongodb = MongoDB()


async def connect_to_mongo() -> None:

    settings = get_settings()
    mongodb.client = AsyncIOMotorClient(settings.mongodb_url)
    mongodb.db = mongodb.client[settings.mongodb_db]
    await mongodb.client.admin.command("ping")


async def close_mongo_connection() -> None:
    """Закрывает подключение. Вызывается при shutdown."""
    if mongodb.client is not None:
        mongodb.client.close()


def get_db() -> AsyncIOMotorDatabase:

    if mongodb.db is None:
        raise RuntimeError("MongoDB не подключена. Вызови connect_to_mongo().")
    return mongodb.db
