# apps/phase2_rag_cli/main.py
import argparse
import os
import textwrap

from newsrag_core import summarize as summarize_phase1
from newsrag_retrieval.ingest import ingest_urls
from newsrag_retrieval.vector_faiss import FaissStore
from newsrag_retrieval.embeddings import embedding_dim
from newsrag_retrieval.retrieve import retrieve as retrieve_vector
from newsrag_retrieval.hybrid import hybrid_retrieve as retrieve_hybrid  # comment this line if you didn't add hybrid.py
from newsrag_retrieval.verify import verify_claims
from newsrag_retrieval.synthesizeesize import synthesize as grounded_summarize


def format_context(hits):
    parts = []
    for i, (m, score) in enumerate(hits, 1):
        url = m.get("url")
        chunk = m.get("chunk")
        snippet = textwrap.shorten((m.get("text") or "").replace("\n", " "), width=900, placeholder="…")
        parts.append(f"[{i}] ({url}#chunk{chunk}) score={score:.3f}\n{snippet}")
    return "\n\n".join(parts)


def diversify_hits(hits, k=6, max_per_url=2):
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


def main():
    p = argparse.ArgumentParser(description="Phase 2/2B RAG CLI")
    p.add_argument("--seed-url", action="append", help="URL to ingest (repeatable)")
    p.add_argument("--question", required=True, help="User question")
    p.add_argument("--k", type=int, default=6, help="Top-k chunks to include")
    p.add_argument("--max-per-url", type=int, default=2, help="Cap chunks per source URL")
    p.add_argument("--db-dir", default=".ragdb", help="Directory for FAISS+metadata")
    p.add_argument("--persist", action="store_true", help="Save index after ingest")
    p.add_argument("--reuse", action="store_true", help="Reuse existing index; skip ingest")
    p.add_argument("--retriever", choices=["hybrid", "vector"], default="hybrid", help="Retrieval method")
    p.add_argument("--alpha", type=float, default=0.6, help="Hybrid weight for vector score (0..1)")
    args = p.parse_args()

    if not args.reuse and not args.seed_url:
        p.error("Provide at least one --seed-url, or use --reuse with an existing --db-dir")

    dim = embedding_dim()

    # Load or (re)build store
    store = None
    if args.reuse and os.path.exists(args.db_dir):
        print("[+] Loading vector store from disk…")
        try:
            store = FaissStore.load(args.db_dir, dim)
        except FileNotFoundError:
            print("[warn] No saved index at", args.db_dir)

    if store is None:
        if not args.seed_url:
            raise SystemExit("No seed URLs provided and no saved index to reuse.")
        print("[+] Ingesting URLs…")
        vecs, metas, _ = ingest_urls(args.seed_url)
        if not vecs:
            raise SystemExit("No docs ingested. Check your URLs or fetcher.")
        print("[+] Building vector store…")
        store = FaissStore(dim)
        store.add(vecs, metas)
        if args.persist:
            print(f"[+] Saving vector store to {args.db_dir}…")
            store.save(args.db_dir)

    # Retrieval
    print(f"[+] Retrieving with: {args.retriever}")
    overfetch = max(args.k * 3, args.k)
    if args.retriever == "hybrid":
        hits_raw = retrieve_hybrid(args.question, store, k=overfetch, alpha=args.alpha)
    else:
        hits_raw = retrieve_vector(args.question, store, k=overfetch)

    hits = diversify_hits(hits_raw, k=args.k, max_per_url=args.max_per_url)
    if not hits:
        raise SystemExit("No results retrieved.")

    # Summarize with Phase-1 summarizer as default
    print("[+] Summarizing…")
    context = format_context(hits)
    answer = grounded_summarize(args.question, context)
    tldr = answer.get("tldr")
    bullets = answer.get("bullets") or []

    # --- Verification pass (Phase 2B) ---
    print("\n[+] Verifying claims against retrieved evidence…")
    claims = [b for b in bullets if isinstance(b, str) and b.strip()]
    ver = verify_claims(claims, hits)

    print("\n=== VERIFICATION ===")
    results = ver.get("results") or []
    if not results and "error" in ver:
        print("Verifier error:", ver["error"])
    elif not results:
        print("No claims to verify.")
    else:
        for r in results:
            ids = r.get("evidence_ids") or []
            tag = r.get("status", "insufficient").upper()
            cite = "[" + ",".join(str(i) for i in ids) + "]" if ids else "[]"
            print(f"- {tag} {cite} {r.get('claim')}")


    # Output
    print("\n=== ANSWER ===")
    print("TL;DR:", tldr)
    print("\nKey Points:")
    for b in bullets:
        print("-", b)

    print("\n=== SOURCES ===")
    for i, (m, score) in enumerate(hits, 1):
        print(f"[{i}] {m['url']} (chunk {m['chunk']}, score {score:.3f})")


if __name__ == "__main__":
    main()
