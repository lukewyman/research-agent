from typing import List, Tuple
from .embeddings import embed_texts

def retrieve(query: str, store, k: int = 8) -> List[Tuple[dict, float]]:
    qvec = embed_texts([query])[0]
    return store.search(qvec, k=k)
