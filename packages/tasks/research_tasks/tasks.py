import os, json, textwrap, time
from typing import List
from .celery_app import app

from research_rag.ingest import ingest_urls
from research_rag.vector_faiss import FaissStore
from research_rag.embeddings import embedding_dim
from research_rag.retrieve import retrieve as retrieve_vector
from research_rag.hybrid import hybrid_retrieve as retrieve_hybrid
from research_rag.synthesize import synthesize as grounded_summarize
from research_rag.verify import verify_claims

RAGDB_ROOT = os.getenv("RAGDB_ROOT", ".ragdb")
EMBED_MODEL = "text-embedding-3-small"

def _dbdir(corpus_id: str) -> str:
    return os.path.join(RAGDB_ROOT, corpus_id)

def _write_manifest(dbdir: str, *, dim: int, doc_count: int):
    os.makedirs(dbdir, exist_ok=True)
    with open(os.path.join(dbdir, "manifest.json"), "w") as f:
        json.dump({"embed_model": EMBED_MODEL, "dim": dim, "doc_count": doc_count}, f, indent=2)

def _diversify(hits, k=6, max_per_url=2):
    out, per = [], {}
    for m, score in hits:
        url = m.get("url")
        if per.get(url, 0) >= max_per_url:
            continue
        out.append((m, score))
        per[url] = per.get(url, 0) + 1
        if len(out) >= k:
            break
    return out

def _labeled_context(hits):
    parts = []
    for i, (m, score) in enumerate(hits, 1):
        snippet = textwrap.shorten((m.get("text") or "").replace("\n"," "), width=900, placeholder="…")
        parts.append(f"[{i}] ({m.get('url')}#chunk{m.get('chunk')}) score={score:.3f}\n{snippet}")
    return "\n\n".join(parts)

@app.task(bind=True, name="ingest_urls_task")
def ingest_urls_task(self, corpus_id: str, urls: List[str]):
    self.update_state(state="STARTED", meta={"step": "fetch"})
    vecs, metas, _ = ingest_urls(urls)
    if not vecs:
        return {"corpus_id": corpus_id, "chunks_indexed": 0, "warning": "No documents ingested"}

    self.update_state(state="PROGRESS", meta={"step": "index", "pct": 50})
    dim = embedding_dim()
    store = FaissStore(dim)
    store.add(vecs, metas)
    dbdir = _dbdir(corpus_id)
    store.save(dbdir)
    _write_manifest(dbdir, dim=dim, doc_count=len(metas))
    self.update_state(state="PROGRESS", meta={"step": "done", "pct": 100})
    return {"corpus_id": corpus_id, "chunks_indexed": len(metas)}

@app.task(bind=True, name="answer_question_task")
def answer_question_task(self, corpus_id: str, question: str, retriever: str = "hybrid",
                         k: int = 6, max_per_url: int = 2, alpha: float = 0.6):
    self.update_state(state="STARTED", meta={"step": "load"})
    dim = embedding_dim()
    dbdir = _dbdir(corpus_id)
    store = FaissStore.load(dbdir, dim)

    self.update_state(state="PROGRESS", meta={"step": "retrieve", "pct": 30})
    overfetch = max(k * 3, k)
    if retriever == "hybrid":
        raw = retrieve_hybrid(question, store, k=overfetch, alpha=alpha)
    else:
        raw = retrieve_vector(question, store, k=overfetch)

    hits = _diversify(raw, k=k, max_per_url=max_per_url)
    if not hits:
        return {"error": "No results retrieved", "tldr": "", "bullets": [], "sources": []}

    self.update_state(state="PROGRESS", meta={"step": "synthesize", "pct": 60})
    ctx = _labeled_context(hits)
    ans = grounded_summarize(question, ctx)
    tldr = ans.get("tldr") or ""
    bullets = ans.get("bullets") or []

    self.update_state(state="PROGRESS", meta={"step": "verify", "pct": 80})
    ver = verify_claims([b for b in bullets if b.strip()], hits)
    verification = ver.get("results") or []

    sources = [{"id": i+1, "url": m["url"], "chunk": m["chunk"], "score": float(score)}
               for i, (m, score) in enumerate(hits)]
    self.update_state(state="PROGRESS", meta={"step": "done", "pct": 100})
    return {"tldr": tldr, "bullets": bullets, "sources": sources, "verification": verification}
