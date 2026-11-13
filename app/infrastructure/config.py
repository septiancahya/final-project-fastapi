from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/orders"
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    redis_url: str = "redis://localhost:6379/2"
    cache_ttl: int = 60
    rate_limit: int = 20
    rate_limit_window: int = 60
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_payment_topic: str = "payment-notifications"
    jwt_secret: str = ""
    access_token_minutes: int = 30
    login_max_attempts: int = 5
    login_block_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


def check_api_settings(settings: Settings) -> None:
    if len(settings.jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET belum di-set atau kurang dari 32 karakter. "
            'Buat dengan: python -c "import secrets; print(secrets.token_hex(32))"'
        )

