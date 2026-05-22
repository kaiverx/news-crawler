from app.crawler.parser import ParsedArticle
from app.sources.models import Source


def article_passes_filters(article: ParsedArticle, source: Source) -> bool:
    topics = {t.lower() for t in article.topics}
    tags = {t.lower() for t in article.tags}

    if source.whitelist_topics:
        allowed = {t.lower() for t in source.whitelist_topics}
        if not topics & allowed:
            return False

    if source.blacklist_topics:
        forbidden = {t.lower() for t in source.blacklist_topics}
        if topics & forbidden:
            return False

    if source.whitelist_tags:
        allowed = {t.lower() for t in source.whitelist_tags}
        if not tags & allowed:
            return False

    if source.blacklist_tags:
        forbidden = {t.lower() for t in source.blacklist_tags}
        if tags & forbidden:
            return False

    return True
