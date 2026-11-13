"""Adapter konkret untuk hashing password (Argon2) dan JWT (HS256)."""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.application.errors import InvalidToken
from app.domain.user import User


class Argon2PasswordHasher:
    def __init__(self):
        self._hasher = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._hasher.verify(password, password_hash)


class JwtTokenService:
    ALGORITHM = "HS256"

    def __init__(self, secret: str, minutes: int):
        self._secret = secret
        self._minutes = minutes

    def issue(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": user.email,
            "role": user.role,
            "scope": " ".join(sorted(user.scopes)),
            "iat": now,
            "exp": now + timedelta(minutes=self._minutes),
        }
        return jwt.encode(claims, self._secret, algorithm=self.ALGORITHM)

    def read(self, token: str) -> dict:
        try:
            return jwt.decode(token, self._secret, algorithms=[self.ALGORITHM])
        except jwt.ExpiredSignatureError as exc:
            raise InvalidToken("Token kedaluwarsa, silakan login lagi") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidToken("Token tidak valid") from exc
