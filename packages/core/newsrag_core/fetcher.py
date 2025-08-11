import os
import requests
from readability import Document
from bs4 import BeautifulSoup
from newsrag_cache import get_redis, key_page, get_json, cache_json

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

PAGE_TTL = int(os.getenv("CACHE_PAGE_TTL_SEC", "21600"))  # 6h default
ENABLE_CACHE = os.getenv("CACHE_ENABLE", "1") != "0"

def fetch_article_text(url: str) -> str:
    r = get_redis() if ENABLE_CACHE else None
    k = key_page(url)
    if r:
        cached = get_json(r, k)
        if cached and isinstance(cached, dict) and "text" in cached:
            return cached["text"]

    resp = requests.get(url, timeout=20, headers={"User-Agent": UA})
    resp.raise_for_status()

    doc = Document(resp.text)
    html = doc.summary()
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p")).strip()

    if len(text) < 500:
        soup_full = BeautifulSoup(resp.text, "html.parser")
        fallback = " ".join(p.get_text(" ", strip=True) for p in soup_full.find_all("p")).strip()
        if len(fallback) > len(text):
            text = fallback

    if r and text:
        cache_json(r, k, {"text": text}, ttl_sec=PAGE_TTL)
    return text
