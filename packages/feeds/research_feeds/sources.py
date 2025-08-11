import os, time, requests, feedparser
from typing import List

# -------- Google News RSS --------
def google_news_rss(topic_query: str, *, hl="en-US", gl="US", ceid="US:en", num: int = 20) -> List[str]:
    # Example: q="trump OR white house"
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(topic_query)}&hl={hl}&gl={gl}&ceid={ceid}"
    feed = feedparser.parse(url)
    urls = []
    for entry in feed.entries[:num]:
        # prefer original link if present; otherwise link
        link = entry.get("link")
        if link:
            urls.append(link)
    return urls

# -------- The Guardian API --------
def guardian_search(api_key: str, q: str, *, page_size: int = 20) -> List[str]:
    # Docs: https://open-platform.theguardian.com/
    # Endpoint: /search?api-key=...&q=...&page-size=...
    url = "https://content.guardianapis.com/search"
    params = {"api-key": api_key, "q": q, "page-size": page_size, "order-by": "newest", "show-fields": "shortUrl"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    resp = data.get("response", {})
    results = resp.get("results", [])
    out = []
    for item in results:
        # webUrl is the canonical article URL you can fetch and extract
        web_url = item.get("webUrl")
        if web_url:
            out.append(web_url)
    return out
