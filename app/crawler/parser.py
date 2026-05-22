from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle


class ParseError(Exception):
    pass


@dataclass
class ParsedArticle:
    url: str
    title: str
    text: str
    author: str | None = None
    published_at: datetime | None = None
    cover_image_url: str | None = None
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class Parser:

    def parse_article(self, url: str, html: str) -> ParsedArticle:
        try:
            article = NewspaperArticle(url)
            article.set_html(html)
            article.parse()
        except Exception as exc:
            raise ParseError(f"newspaper3k не смог распарсить {url}: {exc}") from exc

        if not article.title or not article.text:
            raise ParseError(f"Пустой заголовок или текст для {url}")

        author = article.authors[0] if article.authors else None
        published_at = article.publish_date

        return ParsedArticle(
            url=url,
            title=article.title.strip(),
            text=article.text.strip(),
            author=author,
            published_at=published_at,
            cover_image_url=article.top_image or None,
            tags=list(article.tags) if article.tags else [],
            topics=list(article.meta_keywords) if article.meta_keywords else [],
        )

    def extract_article_links(self, base_url: str, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        base_host = urlparse(base_url).netloc
        links: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)

            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc != base_host:
                continue
            if absolute.rstrip("/") == base_url.rstrip("/"):
                continue

            absolute = absolute.split("#")[0]
            links.add(absolute)

        return sorted(links)
