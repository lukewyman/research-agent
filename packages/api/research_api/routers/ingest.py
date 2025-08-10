from fastapi import APIRouter, HTTPException
from research_api.schemas import IngestRequest, IngestResponse
from research_api.utils import get_db_dir, write_manifest
from research_rag.ingest import ingest_urls
from research_rag.vector_faiss import FaissStore
from research_rag.embeddings import embedding_dim
import os

RAGDB_ROOT = os.getenv("RAGDB_ROOT", ".ragdb")
EMBED_MODEL = "text-embedding-3-small"  # informational only (we use this in research_rag)

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("", response_model=IngestResponse)
def ingest(req: IngestRequest):
    dbdir = get_db_dir(RAGDB_ROOT, req.corpus_id)
    vecs, metas, _ = ingest_urls(req.urls)
    if not vecs:
        raise HTTPException(status_code=400, detail="No documents ingested (bad URLs or empty pages).")

    dim = embedding_dim()
    store = FaissStore(dim)
    store.add(vecs, metas)
    store.save(dbdir)
    write_manifest(dbdir, embed_model=EMBED_MODEL, dim=dim, doc_count=len(metas))
    return IngestResponse(corpus_id=req.corpus_id, chunks_indexed=len(metas))
