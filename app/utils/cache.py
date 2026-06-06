import json
import redis
import asyncio
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

def _sync_delete(*keys):
    try:
        client = get_redis_client()
        client.delete(*keys)
    except Exception:
        pass

def invalidate_cache(*keys):
    if not keys:
        return
    # Run sync Redis in a thread pool so it doesn't block the async event loop
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _sync_delete, *keys)
    except RuntimeError:
        # No running loop (sync context)
        _sync_delete(*keys)