import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app import database, main
from app.articles import dependencies as articles_deps
from app.crawler import dependencies as crawler_deps
from app.crawler.fetcher import Fetcher
from app.crawler.parser import Parser
from app.scheduler import manager as scheduler_manager


@pytest.fixture
async def client(monkeypatch):
    mock_client = AsyncMongoMockClient()
    database.mongodb.client = mock_client
    database.mongodb.db = mock_client["test_db"]

    monkeypatch.setattr(database, "connect_to_mongo", _noop_async)
    monkeypatch.setattr(database, "close_mongo_connection", _noop_async)

    fetcher = Fetcher()
    crawler_deps.deps.fetcher = fetcher
    crawler_deps.deps.parser = Parser()

    class FakeLLM:
        async def close(self):
            pass

        async def rewrite(self, *args, **kwargs):
            raise NotImplementedError

    class FakePublisher:
        async def close(self):
            pass

        async def publish(self, payload):
            return {"status_code": 200, "body": payload}

    articles_deps.deps.publisher = FakePublisher()
    articles_deps.deps.llm = FakeLLM()

    monkeypatch.setattr(main, "init_scheduler", _noop_async)
    monkeypatch.setattr(main, "shutdown_scheduler", _noop_async)
    scheduler_manager.scheduler = None

    transport = ASGITransport(app=main.app)
    async with main.app.router.lifespan_context(main.app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    await fetcher.close()


async def _noop_async(*args, **kwargs):
    return None


async def test_create_list_delete_source(client):
    payload = {"name": "Test", "url": "https://test.com", "schedule": "0 0 * * *"}
    resp = await client.post("/api/v1/sources", json=payload)
    assert resp.status_code == 201
    source = resp.json()
    source_id = source["_id"] if "_id" in source else source["id"]

    resp = await client.get("/api/v1/sources")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.delete(f"/api/v1/sources/{source_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/sources/{source_id}")
    assert resp.status_code == 404


async def test_duplicate_source_url(client):
    payload = {"name": "Test", "url": "https://dup.com", "schedule": "0 0 * * *"}
    r1 = await client.post("/api/v1/sources", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/sources", json=payload)
    assert r2.status_code == 409
