# packages/retrieval/newsrag_retrieval/vector_faiss.py
from __future__ import annotations
from typing import List, Sequence, Tuple, Optional
import numpy as np
import faiss


class FaissStore:
    """
    Flat IP index with cosine-compatible behavior (expects pre-normalized vectors).
    We also keep a NumPy matrix mirror so we can persist/rebuild without relying on
    FAISS's internal serialization.
    """
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self._matrix: Optional[np.ndarray] = None  # rows = vectors
        self._metas: List[dict] = []

    @property
    def metas(self) -> List[dict]:
        return self._metas

    def add(self, vectors: Sequence[Sequence[float]] | np.ndarray, metas: List[dict]) -> None:
        vecs = np.asarray(vectors, dtype="float32")
        if vecs.ndim != 2 or vecs.shape[1] != self.dim:
            raise ValueError(f"Bad shape {vecs.shape}; expected (N, {self.dim})")

        # Maintain matrix mirror for persistence
        if self._matrix is None:
            self._matrix = vecs.copy()
        else:
            self._matrix = np.vstack((self._matrix, vecs))

        self.index.add(vecs)
        self._metas.extend(metas)

    def search(self, query_vecs: Sequence[Sequence[float]] | np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        q = np.asarray(query_vecs, dtype="float32")
        if q.ndim != 2 or q.shape[1] != self.dim:
            raise ValueError(f"Bad query shape {q.shape}; expected (Q, {self.dim})")
        scores, idx = self.index.search(q, k)
        return scores, idx  # scores: (Q,k), idx: (Q,k)

    # ---------- NEW: persistence helpers ----------
    def to_numpy(self) -> Tuple[np.ndarray, List[dict]]:
        """
        Return (matrix, metas) for persistence.
        Matrix is float32 (N, dim) with rows normalized for cosine/IP.
        """
        if self._matrix is None:
            return np.empty((0, self.dim), dtype="float32"), []
        return self._matrix.astype("float32", copy=False), list(self._metas)

    @classmethod
    def from_numpy(cls, vecs: np.ndarray, metas: List[dict], dim: int) -> "FaissStore":
        """
        Rebuild a store from a matrix + metas.
        """
        store = cls(dim)
        if vecs.size:
            store.add(vecs, metas)
        return store

    # (Optional convenience)
    def ntotal(self) -> int:
        return self.index.ntotal
