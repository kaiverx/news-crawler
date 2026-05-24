from app.articles.publisher import ArticlePublisher
from app.articles.rewriter import LLMProvider, build_llm_provider
from app.config import get_settings


class ArticlesDeps:
    publisher: ArticlePublisher | None = None
    llm: LLMProvider | None = None


deps = ArticlesDeps()


async def init_articles_deps() -> None:
    settings = get_settings()
    deps.publisher = ArticlePublisher(settings.main_service_url)
    deps.llm = build_llm_provider(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )


async def close_articles_deps() -> None:
    if deps.publisher is not None:
        await deps.publisher.close()
    if deps.llm is not None:
        await deps.llm.close()


def get_publisher() -> ArticlePublisher:
    if deps.publisher is None:
        raise RuntimeError("Publisher не инициализирован")
    return deps.publisher


def get_llm() -> LLMProvider:
    if deps.llm is None:
        raise RuntimeError("LLM провайдер не инициализирован")
    return deps.llm
