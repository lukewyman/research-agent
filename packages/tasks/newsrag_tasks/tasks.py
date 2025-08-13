# packages/tasks/newsrag_tasks/tasks.py
from __future__ import annotations

from typing import List, Tuple, Dict, Any
import numpy as np

# Celery app
from .celery_app import app

# Feeds → for scheduled polling and enqueuing ingest batches
from newsrag_feeds import fetch_topics_once

# Retrieval plumbing
from newsrag_retrieval.vector_faiss import FaissStore
from newsrag_retrieval.embeddings import embed_texts, embedding_dim, EMBED_MODEL
from newsrag_retrieval.storage import save as storage_save, load as storage_load

# Ingestion (fetch + extract + chunk)
from newsrag_retrieval.ingest import ingest_urls as ingest_urls_sync

# Generation (LLM synthesis); verification is optional
from newsrag_retrieval.synthesize import synthesize  # returns (tldr, bullets)
try:
    from newsrag_retrieval.verify import verify_bullets  # optional Phase 2B
except Exception:  # pragma: no cover
    verify_bullets = None  # type: ignore

# Optional hybrid retrieval; we’ll fall back to vector-only if not present
try:
    from newsrag_retrieval.hybrid import hybrid_retrieve
except Exception:  # pragma: no cover
    hybrid_retrieve = None  # type: ignore


# -------------------------
# Helpers
# -------------------------

def _build_store_from_vectors(vecs: np.ndarray, metas: List[Dict[str, Any]]) -> FaissStore:
    dim = vecs.shape[1] if vecs.size else embedding_dim()
    store = FaissStore(dim)
    if vecs.size:
        store.add(vecs, metas)
    return store


def _vector_retrieve(store: FaissStore, query: str, k: int = 6) -> List[Dict[str, Any]]:
    """Simple vector-only retrieval; returns list of meta dicts with ._score added."""
    q_vec = np.asarray(embed_texts([query])[0], dtype="float32")[None, :]
    scores, idx = store.search(q_vec, k)
    ixs = idx[0]
    scr = scores[0]
    out: List[Dict[str, Any]] = []
    for rank, (i, s) in enumerate(zip(ixs.tolist(), scr.tolist())):
        if i < 0:
            continue
        m = dict(store.metas[i])  # copy
        m["_score"] = float(s)
        m["_rank"] = rank
        out.append(m)
    return out


# -------------------------
# Tasks
# -------------------------

@app.task(bind=True, name="ingest_urls_task")
def ingest_urls_task(self, corpus_id: str, urls: List[str]) -> Dict[str, Any]:
    """
    Fetch, extract & chunk URLs → embed → build FAISS → persist via storage backend (FS or S3).
    Persists three artifacts per corpus: vectors.npy, meta.pkl, manifest.json.
    """
    # 1) Ingest → texts + metas (each meta at least contains 'url', maybe 'title', 'chunk_id', etc.)
    texts, metas = ingest_urls_sync(urls)

    # 2) Embed (already L2-normalized by our embed_texts implementation)
    vecs = np.asarray(embed_texts(texts), dtype="float32")

    # 3) Build store in-memory (for immediate use) and persist artifacts via storage backend
    store = _build_store_from_vectors(vecs, metas)
    matrix, metas_out = store.to_numpy()
    manifest = {"embed_model": EMBED_MODEL, "dim": int(matrix.shape[1] if matrix.size else embedding_dim()),
                "doc_count": len(metas_out)}

    storage_save(corpus_id, matrix, metas_out, manifest)
    return {"corpus_id": corpus_id, "chunks_indexed": len(metas_out), "dim": manifest["dim"]}


@app.task(bind=True, name="answer_question_task")
def answer_question_task(self,
                         corpus_id: str,
                         question: str,
                         retriever: str = "hybrid",
                         k: int = 6,
                         max_per_url: int = 2,
                         alpha: float = 0.6) -> Dict[str, Any]:
    """
    Load persisted store (FS/S3) → retrieve (hybrid or vector) → LLM synth → optional verification.
    Returns TL;DR, bullets, and sources.
    """
    # 1) Load vectors + metas from storage
    vecs, metas, manifest = storage_load(corpus_id)
    dim = int(manifest.get("dim", vecs.shape[1] if vecs.size else embedding_dim()))
    store = FaissStore.from_numpy(vecs, metas, dim)

    # 2) Retrieve
    if retriever == "hybrid" and hybrid_retrieve is not None:
        hits = hybrid_retrieve(
            question=question,
            store=store,
            k=k,
            max_per_url=max_per_url,
            alpha=alpha
        )
        # hits should be a list[meta dict] with scores; if your hybrid returns a different shape, adapt here
    else:
        hits = _vector_retrieve(store, question, k=k)

    # Build contexts for synthesis
    # Expect each hit meta to include 'text' (the chunk); if your meta uses another key, adapt here.
    contexts = [h.get("text", "") for h in hits if h.get("text")]
    sources = [{
        "url": h.get("url"),
        "title": h.get("title"),
        "score": h.get("_score"),
        "rank": h.get("_rank")
    } for h in hits]

    # 3) Synthesize
    tldr, bullets = synthesize(question, contexts)

    # 4) Optional verification pass
    if verify_bullets is not None:
        bullets = verify_bullets(question, bullets, contexts)

    return {
        "tldr": tldr,
        "bullets": bullets,
        "sources": sources,
        "retriever": ("hybrid" if retriever == "hybrid" and hybrid_retrieve else "vector"),
        "corpus_id": corpus_id,
    }


@app.task(bind=True, name="fetch_feeds_task")
def fetch_feeds_task(self, corpus_id: str) -> Dict[str, Any]:
    """
    Poll configured feeds (Google News RSS, Guardian API if key present),
    dedupe via Redis set (handled inside fetch_topics_once), and enqueue ingest batches.
    """
    topics = fetch_topics_once()  # { topic: [new_urls...] }
    enqueued = 0
    for topic, urls in topics.items():
        if not urls:
            continue
        # small batches for nicer embedding throughput vs task overhead
        batch: List[str] = []
        for u in urls:
            batch.append(u)
            if len(batch) >= 8:
                ingest_urls_task.delay(corpus_id, batch)
                enqueued += len(batch)
                batch = []
        if batch:
            ingest_urls_task.delay(corpus_id, batch)
            enqueued += len(batch)

    return {"topics": {k: len(v) for k, v in topics.items()}, "enqueued": enqueued}
