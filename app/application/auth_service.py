"""Use-case autentikasi: register, login (keluarkan JWT), authenticate (verifikasi token + scope)."""
from dataclasses import dataclass

from app.application.errors import (
    AccessDenied,
    InvalidCredentials,
    InvalidToken,
    TooManyLoginAttempts,
    UserAlreadyExists,
)
from app.domain.ports import PasswordHasher, TokenService, UserRepository
from app.domain.user import User


@dataclass(frozen=True)
class CurrentUser:
    email: str
    role: str
    scopes: frozenset[str]

    def can(self, scope: str) -> bool:
        return scope in self.scopes


class AuthService:
    def __init__(self, users: UserRepository, hasher: PasswordHasher,
                 tokens: TokenService, limiter=None):
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._limiter = limiter

    def register(self, email: str, password: str, role: str = "customer") -> User:
        if self._users.get_by_email(email) is not None:
            raise UserAlreadyExists(f"User {email} sudah terdaftar")
        return self._users.add(User(email, self._hasher.hash(password), role))

    def login(self, email: str, password: str) -> str:
        if self._limiter is not None:
            retry_after = self._limiter.blocked_for(email)
            if retry_after:
                raise TooManyLoginAttempts(retry_after)

        user = self._users.get_by_email(email)
        if user is None or not self._hasher.verify(password, user.password_hash):
            if self._limiter is not None:
                self._limiter.record_failure(email)
            raise InvalidCredentials("Email atau password salah")

        if self._limiter is not None:
            self._limiter.reset(email)
        return self._tokens.issue(user)

    def authenticate(self, token: str, required_scopes) -> CurrentUser:
        claims = self._tokens.read(token)
        try:
            user = CurrentUser(
                email=claims["sub"],
                role=claims["role"],
                scopes=frozenset(claims["scope"].split()),
            )
        except KeyError as exc:
            raise InvalidToken(f"Token tidak berisi {exc}") from exc

        missing = [s for s in required_scopes if not user.can(s)]
        if missing:
            raise AccessDenied(f"Butuh scope: {', '.join(missing)}")
        return user
