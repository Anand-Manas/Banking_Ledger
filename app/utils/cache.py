import json
import redis
from app.core.config import settings

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client

def get_cache(key: str):
    try:
        client = get_redis_client()
        data = client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception:
        return None

def set_cache(key: str, value, ttl: int = 60):
    try:
        client = get_redis_client()
        client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass

def invalidate_cache(*keys):
    try:
        client = get_redis_client()
        client.delete(*keys)
    except Exception:
        pass
