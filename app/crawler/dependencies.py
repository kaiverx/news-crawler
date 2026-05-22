from app.config import get_settings
from app.crawler.fetcher import Fetcher
from app.crawler.parser import Parser


class CrawlerDeps:
    fetcher: Fetcher | None = None
    parser: Parser | None = None


deps = CrawlerDeps()


async def init_crawler_deps() -> None:
    settings = get_settings()
    deps.fetcher = Fetcher(max_concurrent=settings.max_crawl_threads)
    deps.parser = Parser()


async def close_crawler_deps() -> None:
    if deps.fetcher is not None:
        await deps.fetcher.close()


def get_fetcher() -> Fetcher:
    if deps.fetcher is None:
        raise RuntimeError("Fetcher не инициализирован")
    return deps.fetcher


def get_parser() -> Parser:
    if deps.parser is None:
        raise RuntimeError("Parser не инициализирован")
    return deps.parser
