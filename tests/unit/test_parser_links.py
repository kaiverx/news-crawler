from app.crawler.parser import Parser


def test_extract_links_filters_external_and_anchors():
    html = """
    <html><body>
      <a href="/news/article-1">A1</a>
      <a href="https://example.com/news/article-2">A2</a>
      <a href="https://other.com/article">External</a>
      <a href="/news/article-1#section">Anchor of A1</a>
      <a href="mailto:test@example.com">Mail</a>
      <a href="javascript:void(0)">JS</a>
    </body></html>
    """
    parser = Parser()
    links = parser.extract_article_links("https://example.com", html)

    assert "https://example.com/news/article-1" in links
    assert "https://example.com/news/article-2" in links
    assert all("other.com" not in link for link in links)
    assert all("mailto:" not in link for link in links)
    assert all("javascript:" not in link for link in links)
    assert len({link for link in links if "article-1" in link}) == 1
