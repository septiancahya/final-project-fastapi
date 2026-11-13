from typing import Protocol

from app.domain.order import Order
from app.domain.user import User


class OrderRepository(Protocol):
    def get(self, order_id: int) -> Order | None: ...

    def save(self, order: Order) -> None: ...


class NotificationPublisher(Protocol):
    def publish_payment_completed(self, order_id: int, amount: int) -> None: ...


class UserRepository(Protocol):
    def add(self, user: User) -> User: ...

    def get_by_email(self, email: str) -> User | None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def issue(self, user: User) -> str: ...

    def read(self, token: str) -> dict: ...
