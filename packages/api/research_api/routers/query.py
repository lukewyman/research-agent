from fastapi import APIRouter, HTTPException
from research_api.schemas import QueryRequest, AnswerResponse, SourceItem
from research_api.utils import get_db_dir, read_manifest
from research_rag.vector_faiss import FaissStore
from research_rag.embeddings import embedding_dim
from research_rag.retrieve import retrieve as retrieve_vector
from research_rag.hybrid import hybrid_retrieve as retrieve_hybrid
from research_rag.synthesize import synthesize as grounded_summarize
from research_rag.verify import verify_claims

import os, textwrap

RAGDB_ROOT = os.getenv("RAGDB_ROOT", ".ragdb")

router = APIRouter(prefix="/query", tags=["query"])

def _format_sources(hits):
    items = []
    for i, (m, score) in enumerate(hits, start=1):
        items.append(SourceItem(id=i, url=m["url"], chunk=m["chunk"], score=round(float(score), 3)))
    return items

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
        snippet = textwrap.shorten((m.get("text") or "").replace("\n", " "), width=900, placeholder="…")
        parts.append(f"[{i}] ({m.get('url')}#chunk{m.get('chunk')}) score={score:.3f}\n{snippet}")
    return "\n\n".join(parts)

@router.post("", response_model=AnswerResponse)
def query(req: QueryRequest):
    dbdir = get_db_dir(RAGDB_ROOT, req.corpus_id)
    try:
        _, dim, _ = read_manifest(dbdir)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Unknown corpus_id; ingest first.")

    # sanity: embedding dim match
    if dim != embedding_dim():
        raise HTTPException(status_code=400, detail="Embedding dimension mismatch; re-ingest with current model.")

    store = FaissStore.load(dbdir, dim)

    overfetch = max(req.k * 3, req.k)
    if req.retriever == "hybrid":
        raw = retrieve_hybrid(req.question, store, k=overfetch, alpha=req.alpha)
    else:
        raw = retrieve_vector(req.question, store, k=overfetch)

    hits = _diversify(raw, k=req.k, max_per_url=req.max_per_url)
    if not hits:
        raise HTTPException(status_code=404, detail="No results retrieved.")

    ctx = _labeled_context(hits)
    ans = grounded_summarize(req.question, ctx)
    tldr = ans.get("tldr") or ""
    bullets = ans.get("bullets") or []

    # verify bullets
    ver = verify_claims([b for b in bullets if b.strip()], hits)
    verification = ver.get("results") or []

    return AnswerResponse(
        tldr=tldr,
        bullets=bullets,
        sources=_format_sources(hits),
        verification=verification,
    )
