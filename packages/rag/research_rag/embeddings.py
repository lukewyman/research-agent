from typing import List
import numpy as np
from openai import OpenAI
from research_core.config import OPENAI_API_KEY

_EMBED_MODEL = "text-embedding-3-small"
_client = OpenAI(api_key=OPENAI_API_KEY)

def embed_texts(texts: List[str]) -> List[List[float]]:
    """Returns L2-normalized embeddings so we can use cosine via inner product."""
    res = _client.embeddings.create(model=_EMBED_MODEL, input=texts)
    arr = np.array([d.embedding for d in res.data], dtype="float32")
    # normalize for cosine similarity with IndexFlatIP
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    arr = arr / norms
    return arr.tolist()

def embedding_dim() -> int:
    """Probe dimension (cached by caller if needed)."""
    return len(embed_texts(["probe"])[0])
