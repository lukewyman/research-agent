import faiss, numpy as np, os, pickle

class FaissStore:
    def __init__(self, dim: int):
        self.index = faiss.IndexFlatIP(dim)
        self.vecs = None
        self.meta = []

    def add(self, vectors, metas):
        v = np.array(vectors, dtype="float32")
        if self.vecs is None:
            self.vecs = v
        else:
            self.vecs = np.vstack([self.vecs, v])
        self.index.add(v)
        self.meta.extend(metas)

    def search(self, qvec, k: int = 8):
        q = np.array([qvec], dtype="float32")
        D, I = self.index.search(q, k)
        out = []
        for rank, idx in enumerate(I[0]):
            if idx == -1: continue
            out.append((self.meta[idx], float(D[0][rank])))
        return out

    # --- NEW: persistence helpers ---
    def save(self, dirpath: str):
        os.makedirs(dirpath, exist_ok=True)
        np.save(os.path.join(dirpath, "vectors.npy"), self.vecs if self.vecs is not None else np.zeros((0, self.index.d), dtype="float32"))
        with open(os.path.join(dirpath, "meta.pkl"), "wb") as f:
            pickle.dump(self.meta, f)

    @classmethod
    def load(cls, dirpath: str, dim: int):
        vectors_path = os.path.join(dirpath, "vectors.npy")
        meta_path = os.path.join(dirpath, "meta.pkl")
        if not (os.path.exists(vectors_path) and os.path.exists(meta_path)):
            raise FileNotFoundError(f"Missing persisted index in {dirpath}")
        vecs = np.load(vectors_path).astype("float32")
        with open(meta_path, "rb") as f:
            metas = pickle.load(f)
        store = cls(dim)
        if vecs.size:
            store.add(vecs, metas)
        return store
