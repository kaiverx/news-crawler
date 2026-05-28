from app.crawler.filters import article_passes_filters
from app.crawler.parser import ParsedArticle
from app.sources.models import Source


def make_article(topics=None, tags=None):
    return ParsedArticle(
        url="https://x.com/a",
        title="t",
        text="t",
        topics=topics or [],
        tags=tags or [],
    )


def make_source(**kwargs):
    base = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "S",
        "url": "https://x.com",
        "enabled": True,
        "schedule": "0 0 * * *",
        "whitelist_topics": [],
        "blacklist_topics": [],
        "whitelist_tags": [],
        "blacklist_tags": [],
        "crawl_depth": 1,
        "max_articles_per_run": 10,
        "last_crawled_at": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    base.update(kwargs)
    return Source.model_validate(base)


def test_passes_without_filters():
    article = make_article(topics=["tech"])
    source = make_source()
    assert article_passes_filters(article, source) is True


def test_whitelist_topic_match():
    article = make_article(topics=["tech", "sport"])
    source = make_source(whitelist_topics=["tech"])
    assert article_passes_filters(article, source) is True


def test_whitelist_topic_no_match():
    article = make_article(topics=["sport"])
    source = make_source(whitelist_topics=["tech"])
    assert article_passes_filters(article, source) is False


def test_blacklist_topic_blocks():
    article = make_article(topics=["spam"])
    source = make_source(blacklist_topics=["spam"])
    assert article_passes_filters(article, source) is False


def test_case_insensitive():
    article = make_article(topics=["TECH"])
    source = make_source(whitelist_topics=["tech"])
    assert article_passes_filters(article, source) is True
