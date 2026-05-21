from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://mongo:27017"
    mongodb_db: str = "crawler_db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://minio:9000"
    s3_bucket: str = "crawler-media"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    # Основной СМИ-сервис
    main_service_url: str = ""

    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # API
    api_key: str = ""  

    # Прочее
    log_level: str = "INFO"
    max_crawl_threads: int = Field(default=10, ge=1, le=100)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:

    return Settings()
