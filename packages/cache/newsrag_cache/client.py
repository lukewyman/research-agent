# packages/cache/newsrag_cache/client.py
from __future__ import annotations
import os, json, hashlib
from typing import Any, Dict, Iterable, List, Optional

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


def get_redis() -> Optional["redis.Redis"]:
    """
    Return a connected Redis client or None if:
      - REDIS_URL missing/empty/invalid
      - redis package missing
      - connectivity probe fails
    """
    if redis is None:
        return None

    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    if not (url.startswith("redis://") or url.startswith("rediss://") or url.startswith("unix://")):
        return None

    try:
        r = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.5,
        )
        r.ping()
        return r
    except Exception:
        return None


def get_json(r: Optional["redis.Redis"], key: str) -> Optional[Any]:
    if r is None:
        return None
    try:
        s = r.get(key)
        return json.loads(s) if s else None
    except Exception:
        return None


def set_json(r: Optional["redis.Redis"], key: str, value: Any, ttl_sec: int = 0) -> None:
    if r is None:
        return
    try:
        payload = json.dumps(value)
        if ttl_sec > 0:
            r.setex(key, ttl_sec, payload)
        else:
            r.set(key, payload)
    except Exception:
        return


# ---------- Back-compat helpers (used by feeds/pump etc.) ----------

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def cache_json(r: Optional["redis.Redis"], key: str, compute_fn, ttl_sec: int = 0) -> Any:
    """
    Read-through cache:
      - If cached present → return it
      - Else compute via compute_fn(), store JSON, return result
    Works even if r is None (just calls compute_fn()).
    """
    cached = get_json(r, key)
    if cached is not None:
        return cached
    val = compute_fn()
    try:
        set_json(r, key, val, ttl_sec=ttl_sec)
    except Exception:
        pass
    return val


def mget_json(r: Optional["redis.Redis"], keys: Iterable[str]) -> List[Optional[Any]]:
    return [get_json(r, k) for k in keys]


def mset_json(r: Optional["redis.Redis"], mapping: Dict[str, Any], ttl_sec: int = 0) -> None:
    for k, v in mapping.items():
        set_json(r, k, v, ttl_sec=ttl_sec)
