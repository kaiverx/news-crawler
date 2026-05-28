from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.articles.dependencies import close_articles_deps, init_articles_deps
from app.articles.repository import ArticleRepository
from app.articles.router import router as articles_router
from app.common.auth import ApiKeyMiddleware
from app.common.logging import RequestContextMiddleware, configure_logging, get_logger
from app.common.metrics import MetricsMiddleware, metrics_response
from app.common.s3 import get_s3
from app.config import get_settings
from app.crawler.dependencies import close_crawler_deps, init_crawler_deps
from app.crawler.repository import CrawlLogRepository
from app.crawler.router import router as crawler_router
from app.database import close_mongo_connection, connect_to_mongo, get_db
from app.scheduler import init_scheduler, shutdown_scheduler
from app.sources.router import router as sources_router

configure_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup_begin")
    await connect_to_mongo()
    db = get_db()

    await ArticleRepository(db).ensure_indexes()
    await CrawlLogRepository(db).ensure_indexes()

    try:
        get_s3()
        log.info("s3_ready")
    except Exception as exc:
        log.warning("s3_init_failed", error=str(exc))

    await init_crawler_deps()
    await init_articles_deps()
    await init_scheduler(db)
    log.info("startup_complete")

    yield

    log.info("shutdown_begin")
    await shutdown_scheduler()
    await close_articles_deps()
    await close_crawler_deps()
    await close_mongo_connection()
    log.info("shutdown_complete")


settings = get_settings()

app = FastAPI(
    title="News Crawler Service",
    description="Внутренний сервис сбора, рерайта и публикации новостей",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(sources_router, prefix="/api/v1")
app.include_router(crawler_router, prefix="/api/v1")
app.include_router(articles_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {"status": "ok", "service": "news-crawler"}


@app.get("/metrics", tags=["system"], include_in_schema=False)
async def metrics():
    return metrics_response()


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "service": "news-crawler",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
