from newsrag_core import fetch_article_text


def test_fetch_article_text():
    url = "https://example.com"
    text = fetch_article_text(url)
    assert isinstance(text, str)
    assert len(text) > 0
