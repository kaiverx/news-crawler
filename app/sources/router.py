from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.common.exceptions import AlreadyExistsError, NotFoundError
from app.database import get_db
from app.sources.models import Source, SourceCreate, SourceUpdate
from app.sources.repository import SourceRepository
from app.sources.service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])

def get_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> SourceService:
    return SourceService(SourceRepository(db))


# --- Эндпоинты ---

@router.get("", response_model=list[Source], summary="Список всех источников")
async def list_sources(
    service: SourceService = Depends(get_service),
) -> list[Source]:
    return await service.list_sources()


@router.post(
    "",
    response_model=Source,
    status_code=status.HTTP_201_CREATED,
    summary="Создать источник",
)
async def create_source(
    payload: SourceCreate,
    service: SourceService = Depends(get_service),
) -> Source:
    try:
        return await service.create_source(payload)
    except AlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{source_id}", response_model=Source, summary="Получить источник по ID")
async def get_source(
    source_id: str,
    service: SourceService = Depends(get_service),
) -> Source:
    try:
        return await service.get_source(source_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{source_id}", response_model=Source, summary="Обновить источник")
async def update_source(
    source_id: str,
    payload: SourceUpdate,
    service: SourceService = Depends(get_service),
) -> Source:
    try:
        return await service.update_source(source_id, payload)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить источник",
)
async def delete_source(
    source_id: str,
    service: SourceService = Depends(get_service),
) -> None:
    try:
        await service.delete_source(source_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{source_id}/enable", response_model=Source, summary="Включить источник")
async def enable_source(
    source_id: str,
    service: SourceService = Depends(get_service),
) -> Source:
    try:
        return await service.set_enabled(source_id, enabled=True)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{source_id}/disable", response_model=Source, summary="Отключить источник")
async def disable_source(
    source_id: str,
    service: SourceService = Depends(get_service),
) -> Source:
    try:
        return await service.set_enabled(source_id, enabled=False)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
