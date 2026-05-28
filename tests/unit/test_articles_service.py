from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from app.articles.models import ArticleStatus
from app.articles.repository import ArticleRepository
from app.articles.rewriter import RewriteParams, RewriteResult
from app.articles.service import ArticleService
from app.common.exceptions import ValidationError


@pytest.fixture
async def filled_db(mock_db):
    await mock_db.articles.insert_one(
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "source_id": ObjectId("507f1f77bcf86cd799439022"),
            "original_url": "https://x.com/a",
            "title": "Title",
            "original_text": "Lorem ipsum text",
            "rewritten_text": None,
            "summary": None,
            "cover_image_url": None,
            "topics": [],
            "tags": [],
            "author": None,
            "published_at_source": None,
            "status": "new",
            "rewrite_params": None,
            "publish_response": None,
            "crawled_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    return mock_db


@pytest.fixture
def service(filled_db):
    publisher = AsyncMock()
    llm = AsyncMock()
    llm.rewrite.return_value = RewriteResult(
        rewritten_text="Rewritten body", summary="Brief summary"
    )
    return ArticleService(filled_db, publisher, llm)


async def test_rewrite_flow(service):
    article = await service.rewrite_article(
        "507f1f77bcf86cd799439011", RewriteParams()
    )
    assert article.status == ArticleStatus.REWRITTEN
    assert article.rewritten_text == "Rewritten body"
    assert article.summary == "Brief summary"


async def test_approve_only_from_new_or_rewritten(service, filled_db):
    await filled_db.articles.update_one(
        {"_id": ObjectId("507f1f77bcf86cd799439011")},
        {"$set": {"status": "published"}},
    )
    with pytest.raises(ValidationError):
        await service.approve("507f1f77bcf86cd799439011")


async def test_publish_requires_approved(service):
    with pytest.raises(ValidationError):
        await service.publish("507f1f77bcf86cd799439011")


async def test_list_filter_by_status(service):
    result = await service.list_articles(status=ArticleStatus.NEW)
    assert result.total == 1
    assert result.items[0].status == ArticleStatus.NEW
