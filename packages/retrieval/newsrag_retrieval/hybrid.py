from typing import List, Tuple
from rank_bm25 import BM25Okapi
import re
from .embeddings import embed_texts

_token = re.compile(r"\w+")

def _tok(s: str) -> List[str]:
    return _token.findall(s.lower())

def hybrid_retrieve(query: str, store, k: int = 8, alpha: float = 0.6) -> List[Tuple[dict, float]]:
    """
    alpha: weight for vector score; (1-alpha) for BM25 score
    Returns list of (meta, combined_score)
    """
    # Vector search
    qvec = embed_texts([query])[0]
    vec_hits = store.search(qvec, k=max(k*5, k))  # over-fetch

    # BM25 over ALL docs in store.meta (uses text in meta)
    corpus = [m.get("text", "") for m in store.meta]
    tokenized = [ _tok(t) for t in corpus ]
    bm25 = BM25Okapi(tokenized)
    bm_scores = bm25.get_scores(_tok(query))

    # Normalize both scores to [0,1] (simple min-max)
    import numpy as np
    vec_scores = np.array([s for _, s in vec_hits], dtype="float32")
    if vec_scores.size == 0:
        return []
    vmin, vmax = float(vec_scores.min()), float(vec_scores.max())
    def norm_v(s): return 0.0 if vmax==vmin else (s - vmin) / (vmax - vmin)

    b = np.array(bm_scores, dtype="float32")
    bmin, bmax = float(b.min()), float(b.max())
    def norm_b(s): return 0.0 if bmax==bmin else (s - bmin) / (bmax - bmin)

    # Combine: for each candidate from vector hits, mix with its BM25
    combined = []
    for meta, vscore in vec_hits:
        idx = store.meta.index(meta)  # meta identity is preserved in list
        score = alpha*norm_v(vscore) + (1-alpha)*norm_b(b[idx])
        combined.append((meta, float(score)))

    # sort & return top-k
    combined.sort(key=lambda x: x[1], reverse=True)
    return combined[:k]
