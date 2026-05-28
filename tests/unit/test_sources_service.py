import pytest

from app.common.exceptions import AlreadyExistsError, NotFoundError
from app.sources.models import SourceCreate, SourceUpdate
from app.sources.repository import SourceRepository
from app.sources.service import SourceService


@pytest.fixture
def service(mock_db):
    return SourceService(SourceRepository(mock_db))


async def test_create_and_get(service):
    payload = SourceCreate(name="S1", url="https://s1.com")
    created = await service.create_source(payload)
    fetched = await service.get_source(str(created.id))
    assert fetched.name == "S1"


async def test_duplicate_url_rejected(service):
    payload = SourceCreate(name="S1", url="https://s1.com")
    await service.create_source(payload)
    with pytest.raises(AlreadyExistsError):
        await service.create_source(SourceCreate(name="S2", url="https://s1.com"))


async def test_update_partial(service):
    created = await service.create_source(SourceCreate(name="S1", url="https://s1.com"))
    updated = await service.update_source(
        str(created.id), SourceUpdate(name="S1-new")
    )
    assert updated.name == "S1-new"
    assert updated.url == "https://s1.com"


async def test_get_unknown(service):
    with pytest.raises(NotFoundError):
        await service.get_source("507f1f77bcf86cd799439011")


async def test_delete(service):
    created = await service.create_source(SourceCreate(name="S1", url="https://s1.com"))
    await service.delete_source(str(created.id))
    with pytest.raises(NotFoundError):
        await service.get_source(str(created.id))


async def test_enable_disable(service):
    created = await service.create_source(SourceCreate(name="S1", url="https://s1.com"))
    disabled = await service.set_enabled(str(created.id), enabled=False)
    assert disabled.enabled is False
    enabled = await service.set_enabled(str(created.id), enabled=True)
    assert enabled.enabled is True
