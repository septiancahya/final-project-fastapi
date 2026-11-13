"""Self-check jalur JWT + RBAC + ownership, tanpa DB/Redis (pakai fake).

Jalankan: python3 tests/test_security.py   (atau: pytest tests/test_security.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.application.auth_service import AuthService, CurrentUser
from app.application.errors import (
    AccessDenied,
    InvalidCredentials,
    InvalidToken,
    TooManyLoginAttempts,
    UserAlreadyExists,
)
from app.application.order_service import OrderService
from app.domain.order import Order, OrderStatus
from app.domain.user import User
from app.infrastructure.security import Argon2PasswordHasher, JwtTokenService

SECRET = "x" * 32


class FakeUserRepo:
    def __init__(self):
        self._by_email = {}

    def add(self, user):
        self._by_email[user.email] = user
        user.id = len(self._by_email)
        return user

    def get_by_email(self, email):
        return self._by_email.get(email)


class FakeLimiter:
    def __init__(self, block=False):
        self.block = block
        self.failures = 0
        self.resets = 0

    def blocked_for(self, email):
        return 30 if self.block else 0

    def record_failure(self, email):
        self.failures += 1

    def reset(self, email):
        self.resets += 1


class FakeOrderRepo:
    def __init__(self, order):
        self.order = order
        self.saved = False

    def get(self, order_id):
        return self.order if order_id == self.order.id else None

    def save(self, order):
        self.saved = True


class FakePublisher:
    def publish_payment_completed(self, order_id, amount):
        pass


def _auth(limiter=None):
    return AuthService(FakeUserRepo(), Argon2PasswordHasher(),
                       JwtTokenService(SECRET, 30), limiter)


def test_jwt_roundtrip_and_tamper():
    tokens = JwtTokenService(SECRET, 30)
    token = tokens.issue(User("a@mail.com", "h", "admin"))
    claims = tokens.read(token)
    assert claims["sub"] == "a@mail.com"
    assert set(claims["scope"].split()) == {"orders:write", "orders:all",
                                            "products:write", "reports:read"}
    try:
        tokens.read(token + "x")  # tampered
        assert False, "token palsu harus ditolak"
    except InvalidToken:
        pass


def test_expired_token_rejected():
    tokens = JwtTokenService(SECRET, -1)  # exp di masa lalu
    token = tokens.issue(User("a@mail.com", "h"))
    try:
        tokens.read(token)
        assert False, "token kedaluwarsa harus ditolak"
    except InvalidToken:
        pass


def test_register_login_and_scope_check():
    auth = _auth(FakeLimiter())
    auth.register("c@mail.com", "rahasia123", role="customer")
    token = auth.login("c@mail.com", "rahasia123")

    # scope yang dimiliki -> lolos
    user = auth.authenticate(token, ["orders:write"])
    assert isinstance(user, CurrentUser) and user.email == "c@mail.com"

    # scope yang tidak dimiliki customer -> AccessDenied
    try:
        auth.authenticate(token, ["products:write"])
        assert False, "customer tak boleh products:write"
    except AccessDenied:
        pass


def test_wrong_password_and_duplicate():
    auth = _auth(FakeLimiter())
    auth.register("c@mail.com", "rahasia123")
    try:
        auth.login("c@mail.com", "salah")
        assert False
    except InvalidCredentials:
        pass
    # email tak ada -> error & pesan sama (anti enumeration)
    try:
        auth.login("tidakada@mail.com", "apapun")
        assert False
    except InvalidCredentials:
        pass
    try:
        auth.register("c@mail.com", "lagi1234")
        assert False
    except UserAlreadyExists:
        pass


def test_login_blocked_when_limited():
    auth = _auth(FakeLimiter(block=True))
    auth.register("c@mail.com", "rahasia123")
    try:
        auth.login("c@mail.com", "rahasia123")  # benar pun ditolak saat diblokir
        assert False
    except TooManyLoginAttempts:
        pass


def test_pay_ownership():
    order = Order(id=1, amount=500, status=OrderStatus.PENDING, customer="owner@mail.com")
    svc = OrderService(FakeOrderRepo(order), FakePublisher())

    owner = CurrentUser("owner@mail.com", "customer", frozenset({"orders:write"}))
    other = CurrentUser("other@mail.com", "customer", frozenset({"orders:write"}))
    admin = CurrentUser("admin@mail.com", "admin",
                        frozenset({"orders:write", "orders:all"}))

    # bukan pemilik -> ditolak
    try:
        svc.pay(1, other)
        assert False, "non-owner tak boleh bayar"
    except AccessDenied:
        pass

    # admin (orders:all) boleh bayar order orang lain
    paid = svc.pay(1, admin)
    assert paid.status == OrderStatus.PAID

    # pemilik boleh bayar order baru
    order2 = Order(id=2, amount=100, status=OrderStatus.PENDING, customer="owner@mail.com")
    svc2 = OrderService(FakeOrderRepo(order2), FakePublisher())
    assert svc2.pay(2, owner).status == OrderStatus.PAID


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("semua test lulus")
