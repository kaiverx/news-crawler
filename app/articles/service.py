import time
from datetime import datetime
from math import ceil
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.articles.models import (
    Article,
    ArticleStatus,
    ArticleUpdate,
    PaginatedArticles,
)
from app.articles.publisher import ArticlePublisher, PublishError
from app.articles.repository import ArticleRepository
from app.articles.rewriter import LLMProvider, RewriteError, RewriteParams
from app.common.exceptions import NotFoundError, ValidationError
from app.common.logging import get_logger
from app.common.metrics import llm_rewrite_duration_seconds
from app.config import get_settings

log = get_logger("articles")


class ArticleService:

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        publisher: ArticlePublisher,
        llm: LLMProvider,
    ):
        self.repo = ArticleRepository(db)
        self.publisher = publisher
        self.llm = llm

    async def list_articles(
        self,
        status: ArticleStatus | None = None,
        source_id: str | None = None,
        topics: list[str] | None = None,
        tags: list[str] | None = None,
        q: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedArticles:
        filter_query: dict[str, Any] = {}

        if status is not None:
            filter_query["status"] = status.value
        if source_id is not None:
            if not ObjectId.is_valid(source_id):
                raise ValidationError(f"Некорректный source_id: {source_id}")
            filter_query["source_id"] = ObjectId(source_id)
        if topics:
            filter_query["topics"] = {"$in": topics}
        if tags:
            filter_query["tags"] = {"$in": tags}
        if q:
            filter_query["$text"] = {"$search": q}

        crawled_filter: dict[str, Any] = {}
        if date_from is not None:
            crawled_filter["$gte"] = date_from
        if date_to is not None:
            crawled_filter["$lte"] = date_to
        if crawled_filter:
            filter_query["crawled_at"] = crawled_filter

        items, total = await self.repo.list_paginated(filter_query, page, limit)
        return PaginatedArticles(
            items=[Article.model_validate(doc) for doc in items],
            total=total,
            page=page,
            limit=limit,
            pages=ceil(total / limit) if total else 0,
        )

    async def get_article(self, article_id: str) -> Article:
        if not ObjectId.is_valid(article_id):
            raise NotFoundError("Article", article_id)
        doc = await self.repo.get_by_id(ObjectId(article_id))
        if doc is None:
            raise NotFoundError("Article", article_id)
        return Article.model_validate(doc)

    async def update_article(self, article_id: str, payload: ArticleUpdate) -> Article:
        if not ObjectId.is_valid(article_id):
            raise NotFoundError("Article", article_id)

        update_data = payload.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value

        updated = await self.repo.update(ObjectId(article_id), update_data)
        if updated is None:
            raise NotFoundError("Article", article_id)
        return Article.model_validate(updated)

    async def delete_article(self, article_id: str) -> None:
        if not ObjectId.is_valid(article_id):
            raise NotFoundError("Article", article_id)
        ok = await self.repo.delete(ObjectId(article_id))
        if not ok:
            raise NotFoundError("Article", article_id)

    async def rewrite_article(self, article_id: str, params: RewriteParams) -> Article:
        article = await self.get_article(article_id)

        if article.status not in (ArticleStatus.NEW, ArticleStatus.REWRITTEN):
            raise ValidationError(
                f"Нельзя запустить рерайт из статуса {article.status.value}"
            )

        await self.repo.update(
            ObjectId(article_id),
            {"status": ArticleStatus.REWRITING.value},
        )

        provider_name = get_settings().llm_provider
        start_ts = time.perf_counter()
        llm_status = "success"

        try:
            result = await self.llm.rewrite(article.title, article.original_text, params)
        except RewriteError as exc:
            llm_status = "error"
            log.warning("rewrite_failed", article_id=article_id, error=str(exc))
            await self.repo.update(
                ObjectId(article_id),
                {"status": ArticleStatus.NEW.value},
            )
            raise ValidationError(f"Рерайт не удался: {exc}") from exc
        finally:
            llm_rewrite_duration_seconds.labels(
                provider=provider_name, status=llm_status
            ).observe(time.perf_counter() - start_ts)

        log.info("article_rewritten", article_id=article_id, provider=provider_name)
        updated = await self.repo.update(
            ObjectId(article_id),
            {
                "rewritten_text": result.rewritten_text,
                "summary": result.summary,
                "rewrite_params": params.model_dump(),
                "status": ArticleStatus.REWRITTEN.value,
            },
        )
        return Article.model_validate(updated)

    async def approve(self, article_id: str) -> Article:
        article = await self.get_article(article_id)
        if article.status not in (ArticleStatus.NEW, ArticleStatus.REWRITTEN):
            raise ValidationError(
                f"Нельзя одобрить статью в статусе {article.status.value}"
            )
        updated = await self.repo.update(
            ObjectId(article_id),
            {"status": ArticleStatus.APPROVED.value},
        )
        log.info("article_approved", article_id=article_id)
        return Article.model_validate(updated)

    async def reject(self, article_id: str) -> Article:
        article = await self.get_article(article_id)
        if article.status in (ArticleStatus.PUBLISHED, ArticleStatus.REJECTED):
            raise ValidationError(
                f"Нельзя отклонить статью в статусе {article.status.value}"
            )
        updated = await self.repo.update(
            ObjectId(article_id),
            {"status": ArticleStatus.REJECTED.value},
        )
        log.info("article_rejected", article_id=article_id)
        return Article.model_validate(updated)

    async def publish(self, article_id: str) -> Article:
        article = await self.get_article(article_id)
        if article.status != ArticleStatus.APPROVED:
            raise ValidationError(
                f"Публиковать можно только approved (текущий статус: {article.status.value})"
            )

        await self.repo.update(
            ObjectId(article_id),
            {"status": ArticleStatus.PUBLISHING.value},
        )

        payload = {
            "title": article.title,
            "text": article.rewritten_text or article.original_text,
            "summary": article.summary,
            "topics": article.topics,
            "tags": article.tags,
            "author": article.author,
            "cover_image_url": article.cover_image_url,
            "original_url": article.original_url,
            "original_published_at": (
                article.published_at_source.isoformat()
                if article.published_at_source
                else None
            ),
        }

        try:
            response = await self.publisher.publish(payload)
        except PublishError as exc:
            log.warning("publish_failed", article_id=article_id, error=str(exc))
            await self.repo.update(
                ObjectId(article_id),
                {"status": ArticleStatus.APPROVED.value},
            )
            raise ValidationError(f"Публикация не удалась: {exc}") from exc

        log.info("article_published", article_id=article_id)
        updated = await self.repo.update(
            ObjectId(article_id),
            {
                "status": ArticleStatus.PUBLISHED.value,
                "publish_response": response,
            },
        )
        return Article.model_validate(updated)
