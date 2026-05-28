import httpx
from bson import ObjectId

from app.articles.models import Article
from app.articles.repository import ArticleRepository
from app.common.exceptions import NotFoundError, ValidationError
from app.common.s3 import S3Storage


class CoverService:

    def __init__(self, repo: ArticleRepository, s3: S3Storage):
        self.repo = repo
        self.s3 = s3

    async def upload_from_bytes(
        self, article_id: str, data: bytes, content_type: str
    ) -> Article:
        if not ObjectId.is_valid(article_id):
            raise NotFoundError("Article", article_id)
        if await self.repo.get_by_id(ObjectId(article_id)) is None:
            raise NotFoundError("Article", article_id)

        if not content_type.startswith("image/"):
            raise ValidationError(f"Ожидалось image/*, получено {content_type}")

        url = await self.s3.upload_bytes(data, content_type)
        updated = await self.repo.update(
            ObjectId(article_id), {"cover_image_url": url}
        )
        return Article.model_validate(updated)

    async def fetch_from_original_url(self, article_id: str) -> Article:
        if not ObjectId.is_valid(article_id):
            raise NotFoundError("Article", article_id)
        doc = await self.repo.get_by_id(ObjectId(article_id))
        if doc is None:
            raise NotFoundError("Article", article_id)

        source_url = doc.get("cover_image_url")
        if not source_url:
            raise ValidationError("У статьи нет cover_image_url для скачивания")

        if source_url.startswith(self.s3.endpoint):
            return Article.model_validate(doc)

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                response = await client.get(source_url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ValidationError(f"Не удалось скачать обложку: {exc}") from exc

        content_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
        if not content_type.startswith("image/"):
            raise ValidationError(f"Скачан не image (content-type={content_type})")

        url = await self.s3.upload_bytes(response.content, content_type)
        updated = await self.repo.update(
            ObjectId(article_id), {"cover_image_url": url}
        )
        return Article.model_validate(updated)
