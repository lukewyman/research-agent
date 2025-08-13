import os, io, json, pickle
from typing import Tuple, List
import numpy as np

BACKEND = os.getenv("STORAGE_BACKEND", "fs")  # "fs" | "s3"
RAGDB_ROOT = os.getenv("RAGDB_ROOT", ".ragdb")
BUCKET = os.getenv("S3_BUCKET", "")
PREFIX = os.getenv("S3_PREFIX", "ragdb")

def _fs_paths(corpus_id: str):
    d = os.path.join(RAGDB_ROOT, corpus_id)
    return d, os.path.join(d, "vectors.npy"), os.path.join(d, "meta.pkl"), os.path.join(d, "manifest.json")

def save_fs(corpus_id: str, vecs: np.ndarray, metas: List[dict], manifest: dict):
    os.makedirs(_fs_paths(corpus_id)[0], exist_ok=True)
    _, v, m, man = _fs_paths(corpus_id)
    np.save(v, vecs)
    with open(m, "wb") as f: pickle.dump(metas, f)
    with open(man, "w") as f: json.dump(manifest, f, indent=2)

def load_fs(corpus_id: str) -> Tuple[np.ndarray, List[dict], dict]:
    _, v, m, man = _fs_paths(corpus_id)
    vecs = np.load(v).astype("float32")
    with open(m, "rb") as f: metas = pickle.load(f)
    with open(man, "r") as f: manifest = json.load(f)
    return vecs, metas, manifest

def _s3():
    import boto3
    return boto3.client("s3")

def _s3_keys(corpus_id: str):
    base = f"{PREFIX}/{corpus_id}"
    return f"{base}/vectors.npy", f"{base}/meta.pkl", f"{base}/manifest.json"

def save_s3(corpus_id: str, vecs: np.ndarray, metas: List[dict], manifest: dict):
    s3 = _s3()
    k_vec, k_meta, k_man = _s3_keys(corpus_id)
    b = io.BytesIO(); np.save(b, vecs); b.seek(0)
    s3.put_object(Bucket=BUCKET, Key=k_vec, Body=b.getvalue())
    s3.put_object(Bucket=BUCKET, Key=k_meta, Body=pickle.dumps(metas))
    s3.put_object(Bucket=BUCKET, Key=k_man, Body=json.dumps(manifest).encode("utf-8"))

def load_s3(corpus_id: str) -> Tuple[np.ndarray, List[dict], dict]:
    s3 = _s3()
    k_vec, k_meta, k_man = _s3_keys(corpus_id)
    vec_obj = s3.get_object(Bucket=BUCKET, Key=k_vec)["Body"].read()
    meta_obj = s3.get_object(Bucket=BUCKET, Key=k_meta)["Body"].read()
    man_obj  = s3.get_object(Bucket=BUCKET, Key=k_man)["Body"].read()
    vecs = np.load(io.BytesIO(vec_obj)).astype("float32")
    metas = pickle.loads(meta_obj)
    manifest = json.loads(man_obj.decode("utf-8"))
    return vecs, metas, manifest

def save(corpus_id: str, vecs: np.ndarray, metas: List[dict], manifest: dict):
    return save_s3(corpus_id, vecs, metas, manifest) if BACKEND == "s3" else save_fs(corpus_id, vecs, metas, manifest)

def load(corpus_id: str) -> Tuple[np.ndarray, List[dict], dict]:
    return load_s3(corpus_id) if BACKEND == "s3" else load_fs(corpus_id)
