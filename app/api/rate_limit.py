import time
from fastapi import Request, HTTPException
from app.infrastructure.config import get_settings
from app.infrastructure.redis import cache

settings = get_settings()

def rate_limit(request: Request) -> None:
    now = int(time.time())
    key = f"ratelimit:{request.client.host}:{now // settings.rate_limit_window}"
    count = cache.incr(key)
    if count == 1:
        cache.expire(key, settings.rate_limit_window)
    if count > settings.rate_limit:
        retry_after = str(settings.rate_limit_window - now % settings.rate_limit_window)
        raise HTTPException(429, "Terlalu banyak request",
                            headers={"Retry-After": retry_after})