from typing import List, Tuple
from research_core.fetcher import fetch_article_text
from .chunking import simple_chunks
from .embeddings import embed_texts

def ingest_urls(urls: List[str]) -> Tuple[list, list, list]:
    """
    Fetch each URL, chunk content, embed chunks.
    Returns (vectors, metas, texts) in aligned order.
    meta = { "url": str, "chunk": int, "text": str }
    """
    all_texts, metas = [], []
    for url in urls:
        try:
            text = fetch_article_text(url)
        except Exception as e:
            # Skip bad URLs but continue the batch
            print(f"[warn] failed to fetch {url}: {e}")
            continue
        for i, chunk in enumerate(simple_chunks(text)):
            metas.append({"url": url, "chunk": i, "text": chunk})
            all_texts.append(chunk)

    if not all_texts:
        return [], [], []

    vecs = embed_texts(all_texts)
    return vecs, metas, all_texts
