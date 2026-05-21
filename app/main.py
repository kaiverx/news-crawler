
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import close_mongo_connection, connect_to_mongo
from app.sources.router import router as sources_router


@asynccontextmanager
async def lifespan(app: FastAPI):
   
    await connect_to_mongo()
    yield

    await close_mongo_connection()


settings = get_settings()

app = FastAPI(
    title="News Crawler Service",
    description="Внутренний сервис сбора, рерайта и публикации новостей",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(sources_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Health-check для Docker и Kubernetes probes."""
    return {"status": "ok", "service": "news-crawler"}


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "service": "news-crawler",
        "version": "0.1.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
