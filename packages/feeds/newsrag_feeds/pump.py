import os, time
from typing import Dict, List, Set
from newsrag_cache import get_redis, sha1
from .sources import google_news_rss, guardian_search

# Env knobs
FEEDS_TOPICS = os.getenv("FEEDS_TOPICS", "us politics,technology").split(",")
FEEDS_USE_GUARDIAN = os.getenv("FEEDS_USE_GUARDIAN", "1") != "0"
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "")

SEEN_SET = os.getenv("FEEDS_SEEN_SET", "feeds:seen_urls")   # Redis set key
MAX_PER_TOPIC = int(os.getenv("FEEDS_MAX_PER_TOPIC", "12"))

def fetch_topics_once() -> Dict[str, List[str]]:
    """Return {topic: [new_url,...]} (deduped against Redis set)."""
    r = get_redis()
    seen_key = SEEN_SET
    out: Dict[str, List[str]] = {}

    for raw_topic in FEEDS_TOPICS:
        topic = raw_topic.strip()
        if not topic:
            continue
        urls: List[str] = []

        # Google News RSS (primary)
        try:
            urls += google_news_rss(topic, num=MAX_PER_TOPIC)
        except Exception:
            pass

        # Guardian (optional)
        if FEEDS_USE_GUARDIAN and GUARDIAN_API_KEY:
            try:
                urls += guardian_search(GUARDIAN_API_KEY, topic, page_size=MAX_PER_TOPIC)
            except Exception:
                pass

        # Deduplicate within this batch
        urls = list(dict.fromkeys(urls))  # order-preserving unique

        # Cross-batch dedupe in Redis
        new_urls = []
        for u in urls:
            h = sha1(u)
            # SADD returns 1 if added (i.e., not seen before)
            if r.sadd(seen_key, h) == 1:
                new_urls.append(u)

        out[topic] = new_urls
    return out
