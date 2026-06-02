import redis
from app.core.config import settings

redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)

def get_redis():
    return redis.Redis(connection_pool=redis_pool)
