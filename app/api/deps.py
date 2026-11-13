from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.order_service import OrderService
from app.infrastructure.config import get_settings
from app.infrastructure.database import get_db
from app.infrastructure.kafka_producer import KafkaNotificationPublisher
from app.infrastructure.login_limiter import RedisLoginAttemptLimiter
from app.infrastructure.redis import get_redis
from app.infrastructure.repositories import (
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.security import Argon2PasswordHasher, JwtTokenService


@lru_cache
def get_notification_publisher() -> KafkaNotificationPublisher:
    settings = get_settings()
    return KafkaNotificationPublisher(settings.kafka_bootstrap_servers, settings.kafka_payment_topic)


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    repository = SqlAlchemyOrderRepository(db)
    publisher = get_notification_publisher()
    return OrderService(repository, publisher)


def get_product_repository(db: Session = Depends(get_db)) -> SqlAlchemyProductRepository:
    return SqlAlchemyProductRepository(db)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    settings = get_settings()
    return AuthService(
        SqlAlchemyUserRepository(db),
        Argon2PasswordHasher(),
        JwtTokenService(settings.jwt_secret, settings.access_token_minutes),
        RedisLoginAttemptLimiter(get_redis(), settings.login_max_attempts,
                                 settings.login_block_seconds),
    )
