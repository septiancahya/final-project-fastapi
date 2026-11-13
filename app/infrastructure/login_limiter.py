"""Pembatas percobaan login berbasis Redis (anti brute-force).

Pola INCR + EXPIRE seperti app/api/rate_limit.py. Dihitung per email: setelah
`max_attempts` kegagalan berturut, login diblokir selama `block_seconds`.
"""
from redis import Redis


class RedisLoginAttemptLimiter:
    def __init__(self, redis: Redis, max_attempts: int, block_seconds: int):
        self._redis = redis
        self._max_attempts = max_attempts
        self._block_seconds = block_seconds

    def _key(self, email: str) -> str:
        return f"loginfail:{email}"

    def blocked_for(self, email: str) -> int:
        count = self._redis.get(self._key(email))
        if count is not None and int(count) >= self._max_attempts:
            return self._redis.ttl(self._key(email))
        return 0

    def record_failure(self, email: str) -> None:
        key = self._key(email)
        count = self._redis.incr(key)
        if count == 1:
            self._redis.expire(key, self._block_seconds)

    def reset(self, email: str) -> None:
        self._redis.delete(self._key(email))
