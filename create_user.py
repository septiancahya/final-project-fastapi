"""Buat user yang bisa login (password di-hash Argon2).

Contoh:
    python3 create_user.py --email admin@mail.com --role admin
    python3 create_user.py --email customer1@mail.com --role customer
"""
import argparse
from getpass import getpass

from app.application.auth_service import AuthService
from app.application.errors import UserAlreadyExists
from app.infrastructure.config import get_settings
from app.infrastructure.database import SessionLocal
from app.infrastructure.repositories import SqlAlchemyUserRepository
from app.infrastructure.security import Argon2PasswordHasher, JwtTokenService


def main() -> None:
    parser = argparse.ArgumentParser(description="Buat user baru")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("customer", "admin"), default="customer")
    args = parser.parse_args()

    password = getpass("Password (min 8 karakter): ")
    if len(password) < 8:
        raise SystemExit("Password minimal 8 karakter")

    settings = get_settings()
    db = SessionLocal()
    try:
        auth = AuthService(
            SqlAlchemyUserRepository(db),
            Argon2PasswordHasher(),
            JwtTokenService(settings.jwt_secret or "x" * 32, settings.access_token_minutes),
        )
        try:
            user = auth.register(args.email, password, role=args.role)
        except UserAlreadyExists as exc:
            raise SystemExit(str(exc))
        print(f"User dibuat: {user.email} (role={user.role}, id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
