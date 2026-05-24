from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.articles.dependencies import get_llm, get_publisher
from app.articles.models import (
    Article,
    ArticleStatus,
    ArticleUpdate,
    PaginatedArticles,
)
from app.articles.publisher import ArticlePublisher
from app.articles.rewriter import LLMProvider, RewriteParams
from app.articles.service import ArticleService
from app.common.exceptions import NotFoundError, ValidationError
from app.database import get_db

router = APIRouter(prefix="/articles", tags=["articles"])


def get_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    publisher: ArticlePublisher = Depends(get_publisher),
    llm: LLMProvider = Depends(get_llm),
) -> ArticleService:
    return ArticleService(db, publisher, llm)


def _csv_to_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("", response_model=PaginatedArticles, summary="Список статей с фильтрами")
async def list_articles(
    status_filter: ArticleStatus | None = Query(default=None, alias="status"),
    source_id: str | None = Query(default=None),
    topics: str | None = Query(default=None, description="CSV: tech,politics"),
    tags: str | None = Query(default=None, description="CSV: ai,robotics"),
    q: str | None = Query(default=None, description="Полнотекстовый поиск"),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    service: ArticleService = Depends(get_service),
) -> PaginatedArticles:
    try:
        return await service.list_articles(
            status=status_filter,
            source_id=source_id,
            topics=_csv_to_list(topics),
            tags=_csv_to_list(tags),
            q=q,
            date_from=date_from,
            date_to=date_to,
            page=page,
            limit=limit,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{article_id}", response_model=Article, summary="Получить статью по ID")
async def get_article(
    article_id: str,
    service: ArticleService = Depends(get_service),
) -> Article:
    try:
        return await service.get_article(article_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{article_id}", response_model=Article, summary="Ручное обновление статьи")
async def update_article(
    article_id: str,
    payload: ArticleUpdate,
    service: ArticleService = Depends(get_service),
) -> Article:
    try:
        return await service.update_article(article_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить статью",
)
async def delete_article(
    article_id: str,
    service: ArticleService = Depends(get_service),
) -> None:
    try:
        await service.delete_article(article_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{article_id}/rewrite",
    response_model=Article,
    summary="Запустить рерайт через LLM",
)
async def rewrite_article(
    article_id: str,
    params: RewriteParams,
    service: ArticleService = Depends(get_service),
) -> Article:
    try:
        return await service.rewrite_article(article_id, params)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{article_id}/approve", response_model=Article, summary="Одобрить статью")
async def approve_article(
    article_id: str,
    service: ArticleService = Depends(get_service),
) -> Article:
    try:
        return await service.approve(article_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{article_id}/reject", response_model=Article, summary="Отклонить статью")
async def reject_article(
    article_id: str,
    service: ArticleService = Depends(get_service),
) -> Article:
    try:
        return await service.reject(article_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post(
    "/{article_id}/publish",
    response_model=Article,
    summary="Опубликовать статью в основной сервис",
)
async def publish_article(
    article_id: str,
    service: ArticleService = Depends(get_service),
) -> Article:
    try:
        return await service.publish(article_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
