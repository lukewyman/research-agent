import os, json
from typing import Tuple

def get_db_dir(root: str, corpus_id: str) -> str:
    return os.path.join(root, corpus_id)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def write_manifest(dbdir: str, *, embed_model: str, dim: int, doc_count: int):
    ensure_dir(dbdir)
    manifest = {
        "embed_model": embed_model,
        "dim": dim,
        "doc_count": doc_count,
    }
    with open(os.path.join(dbdir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

def read_manifest(dbdir: str) -> Tuple[str, int, int]:
    path = os.path.join(dbdir, "manifest.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No manifest at {path}")
    with open(path) as f:
        m = json.load(f)
    return m["embed_model"], int(m["dim"]), int(m["doc_count"])
