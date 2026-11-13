from redis import Redis
from functools import lru_cache
from app.infrastructure.config import get_settings

settings = get_settings()
@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url)
cache = get_redis()