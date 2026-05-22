from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.articles.repository import ArticleRepository
from app.config import get_settings
from app.crawler.dependencies import close_crawler_deps, init_crawler_deps
from app.crawler.repository import CrawlLogRepository
from app.crawler.router import router as crawler_router
from app.database import close_mongo_connection, connect_to_mongo, get_db
from app.scheduler import init_scheduler, shutdown_scheduler
from app.sources.router import router as sources_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    db = get_db()

    await ArticleRepository(db).ensure_indexes()
    await CrawlLogRepository(db).ensure_indexes()

    await init_crawler_deps()
    await init_scheduler(db)

    yield

    await shutdown_scheduler()
    await close_crawler_deps()
    await close_mongo_connection()


settings = get_settings()

app = FastAPI(
    title="News Crawler Service",
    description="Внутренний сервис сбора, рерайта и публикации новостей",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(sources_router, prefix="/api/v1")
app.include_router(crawler_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {"status": "ok", "service": "news-crawler"}


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "service": "news-crawler",
        "version": "0.2.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
