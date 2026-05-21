from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.common.objectid import PyObjectId


class SourceBase(BaseModel):

    name: Annotated[str, Field(min_length=1, max_length=200, description="Название источника")]
    url: Annotated[str, Field(min_length=1, description="Базовый URL источника")]
    enabled: bool = Field(default=True, description="Активен ли источник")
    schedule: Annotated[
        str,
        Field(
            description="Cron-выражение для расписания обхода",
            examples=["0 */2 * * *"],  # каждые 2 часа
        ),
    ] = "0 */2 * * *"
    whitelist_topics: list[str] = Field(default_factory=list)
    blacklist_topics: list[str] = Field(default_factory=list)
    whitelist_tags: list[str] = Field(default_factory=list)
    blacklist_tags: list[str] = Field(default_factory=list)
    crawl_depth: int = Field(default=1, ge=1, le=5, description="Глубина обхода (1–5)")
    max_articles_per_run: int = Field(default=50, ge=1, le=1000)


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    schedule: str | None = None
    whitelist_topics: list[str] | None = None
    blacklist_topics: list[str] | None = None
    whitelist_tags: list[str] | None = None
    blacklist_tags: list[str] | None = None
    crawl_depth: int | None = Field(default=None, ge=1, le=5)
    max_articles_per_run: int | None = Field(default=None, ge=1, le=1000)


class Source(SourceBase):
    """
    Схема для отдачи клиенту в HTTP-ответе.

    Содержит ВСЕ поля, включая id и временные метки.
    """
    id: PyObjectId = Field(alias="_id", description="Идентификатор источника")
    last_crawled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # populate_by_name=True — позволяет принимать поле и как `_id` (из Mongo),
    #                        и как `id` (из API). Удобно для конвертации в обе стороны.
    # arbitrary_types_allowed=True — нужно, потому что ObjectId не встроенный тип.
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
