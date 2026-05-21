from bson import ObjectId

from app.common.exceptions import AlreadyExistsError, NotFoundError
from app.sources.models import Source, SourceCreate, SourceUpdate
from app.sources.repository import SourceRepository


class SourceService:

    def __init__(self, repository: SourceRepository):
        self.repository = repository

    async def list_sources(self) -> list[Source]:
        """Возвращает список всех источников."""
        documents = await self.repository.list_all()
        return [Source.model_validate(doc) for doc in documents]

    async def get_source(self, source_id: str) -> Source:
        """
        Получает источник по строковому id.

        Бросает NotFoundError, если:
          - id не валидный ObjectId
          - источника с таким id нет в БД
        """
        if not ObjectId.is_valid(source_id):
            raise NotFoundError("Source", source_id)

        doc = await self.repository.get_by_id(ObjectId(source_id))
        if doc is None:
            raise NotFoundError("Source", source_id)
        return Source.model_validate(doc)

    async def create_source(self, payload: SourceCreate) -> Source:

        existing = await self.repository.get_by_url(payload.url)
        if existing is not None:
            raise AlreadyExistsError("Source", "url", payload.url)

        created = await self.repository.create(payload.model_dump())
        return Source.model_validate(created)

    async def update_source(self, source_id: str, payload: SourceUpdate) -> Source:

        if not ObjectId.is_valid(source_id):
            raise NotFoundError("Source", source_id)

        update_data = payload.model_dump(exclude_unset=True)

        if "url" in update_data:
            existing = await self.repository.get_by_url(update_data["url"])
            if existing is not None and str(existing["_id"]) != source_id:
                raise AlreadyExistsError("Source", "url", update_data["url"])

        updated = await self.repository.update(ObjectId(source_id), update_data)
        if updated is None:
            raise NotFoundError("Source", source_id)
        return Source.model_validate(updated)

    async def delete_source(self, source_id: str) -> None:
        if not ObjectId.is_valid(source_id):
            raise NotFoundError("Source", source_id)

        deleted = await self.repository.delete(ObjectId(source_id))
        if not deleted:
            raise NotFoundError("Source", source_id)

    async def set_enabled(self, source_id: str, enabled: bool) -> Source:

        return await self.update_source(source_id, SourceUpdate(enabled=enabled))
