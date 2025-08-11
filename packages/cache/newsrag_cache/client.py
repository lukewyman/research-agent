import json, os
from typing import Any, Iterable, List, Tuple
import redis

def get_redis() -> redis.Redis:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/2")  # separate DB from Celery
    return redis.from_url(url, decode_responses=True)

def cache_json(r: redis.Redis, key: str, value: Any, ttl_sec: int | None = None):
    payload = json.dumps(value, ensure_ascii=False)
    if ttl_sec:
        r.setex(key, ttl_sec, payload)
    else:
        r.set(key, payload)

def get_json(r: redis.Redis, key: str) -> Any | None:
    s = r.get(key)
    return None if s is None else json.loads(s)

def mget_json(r: redis.Redis, keys: List[str]) -> List[Any | None]:
    values = r.mget(keys)
    return [None if v is None else json.loads(v) for v in values]

def mset_json(r: redis.Redis, items: List[Tuple[str, Any]], ttl_sec: int | None = None):
    p = r.pipeline()
    for k, v in items:
        if ttl_sec:
            p.setex(k, ttl_sec, json.dumps(v, ensure_ascii=False))
        else:
            p.set(k, json.dumps(v, ensure_ascii=False))
    p.execute()
