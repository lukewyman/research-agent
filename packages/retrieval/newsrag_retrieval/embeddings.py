from typing import List
import os
import numpy as np
from openai import OpenAI
from newsrag_core.config import OPENAI_API_KEY
from newsrag_cache import get_redis, key_embed, mget_json, mset_json

_EMBED_MODEL = "text-embedding-3-small"
_client = OpenAI(api_key=OPENAI_API_KEY)

EMBED_TTL = int(os.getenv("CACHE_EMBED_TTL_SEC", "2592000"))  # 30d
ENABLE_CACHE = os.getenv("CACHE_ENABLE", "1") != "0"

def _normalize_rows(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return (arr / norms).astype("float32")

def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embedding with Redis cache. Returns L2-normalized vectors for cosine via IP."""
    if not texts:
        return []

    if ENABLE_CACHE:
        r = get_redis()
        keys = [key_embed(_EMBED_MODEL, t) for t in texts]
        cached = mget_json(r, keys)
        missing_idx = [i for i, v in enumerate(cached) if v is None]
        if missing_idx:
            to_embed = [texts[i] for i in missing_idx]
            res = _client.embeddings.create(model=_EMBED_MODEL, input=to_embed)
            new_vecs = np.array([d.embedding for d in res.data], dtype="float32")
            new_vecs = _normalize_rows(new_vecs)
            # write back to cache
            mset_json(r, [(keys[i], new_vecs[j].tolist()) for j, i in enumerate(missing_idx)], ttl_sec=EMBED_TTL)
            # merge into cached list
            for j, i in enumerate(missing_idx):
                cached[i] = new_vecs[j].tolist()
        # All entries now present
        return cached  # type: ignore[return-value]

    # No cache path
    res = _client.embeddings.create(model=_EMBED_MODEL, input=texts)
    arr = np.array([d.embedding for d in res.data], dtype="float32")
    arr = _normalize_rows(arr)
    return arr.tolist()

def embedding_dim() -> int:
    # single probe, cached by caller if needed
    return len(embed_texts(["probe"])[0])
