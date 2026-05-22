from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.common.objectid import PyObjectId


class ArticleStatus(str, Enum):
    NEW = "new"
    REWRITING = "rewriting"
    REWRITTEN = "rewritten"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ArticleBase(BaseModel):
    source_id: PyObjectId
    original_url: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    original_text: str
    rewritten_text: str | None = None
    summary: str | None = None
    cover_image_url: str | None = None
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    author: str | None = None
    published_at_source: datetime | None = None
    status: ArticleStatus = ArticleStatus.NEW
    rewrite_params: dict[str, Any] | None = None
    publish_response: dict[str, Any] | None = None


class ArticleCreate(ArticleBase):
    pass


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    original_text: str | None = None
    rewritten_text: str | None = None
    summary: str | None = None
    cover_image_url: str | None = None
    topics: list[str] | None = None
    tags: list[str] | None = None
    author: str | None = None
    status: ArticleStatus | None = None


class Article(ArticleBase):
    id: PyObjectId = Field(alias="_id")
    crawled_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class PaginatedArticles(BaseModel):
    items: list[Article]
    total: int
    page: int
    limit: int
    pages: int
