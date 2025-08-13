# packages/core/newsrag_core/fetcher.py
from __future__ import annotations

import os
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from newsrag_cache.client import get_redis, get_json, set_json


DEFAULT_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SEC", "15"))
USER_AGENT = os.getenv(
    "HTTP_USER_AGENT",
    "newsrag-bot/0.1 (+https://example.com) python-httpx",
)


def _fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    with httpx.Client(follow_redirects=True, timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _html_to_text(html: str) -> str:
    """
    Very lightweight readability:
    - strip <script>/<style>
    - return visible text, normalized
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    # Prefer article/main if present
    root = soup.find("article") or soup.find("main") or soup.body or soup
    text = root.get_text(separator=" ", strip=True)

    # If nothing, try the title as a minimum signal
    if not text:
        title = (soup.title.string.strip() if soup.title and soup.title.string else "").strip()
        text = title

    # Normalize whitespace
    return " ".join(text.split())


def fetch_article_text(url: str) -> str:
    """
    Fetches a URL and returns plain text content.
    Uses Redis cache when available; gracefully no-ops if Redis is absent.
    """
    r = get_redis()  # may be None in tests/dev
    cache_key = f"page:{url}"

    cached = get_json(r, cache_key)
    if isinstance(cached, str) and cached:
        return cached

    try:
        html = _fetch_html(url)
        text = _html_to_text(html)
    except Exception as e:
        # Best-effort fallback if the request/parsing fails
        text = f""  # keep empty; callers can handle empty if needed
        # You could log 'e' to your logger here if you have one

    # Cache best-effort result (even empty) to avoid hammering hosts during tests/dev
    ttl = int(os.getenv("CACHE_PAGE_TTL_SEC", "21600"))  # 6 hours default
    try:
        set_json(r, cache_key, text, ttl_sec=ttl)
    except Exception:
        pass  # never let cache errors fail core logic

    return text
