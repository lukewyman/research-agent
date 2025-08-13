# packages/cache/newsrag_cache/__init__.py
from __future__ import annotations

# Primary cache client API
from .client import (
    get_redis,
    get_json,
    set_json,
    cache_json,
    mget_json,
    mset_json,
    sha1,
)

__all__ = [
    "get_redis",
    "get_json",
    "set_json",
    "cache_json",
    "mget_json",
    "mset_json",
    "sha1",
]

# --- Back-compat: re-export everything public from keys.py if present ---
try:
    from . import keys as _keys  # noqa: F401
    for _name in dir(_keys):
        if not _name.startswith("_"):
            globals()[_name] = getattr(_keys, _name)
            __all__.append(_name)
except Exception:
    # If keys.py doesn't exist or raises on import, ignore gracefully
    pass
