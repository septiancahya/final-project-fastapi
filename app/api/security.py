"""Skema OAuth2 Bearer + dependency get_current_user untuk FastAPI.

Scope dicek terpusat di sini (lewat AuthService). Endpoint tinggal menyatakan
scope yang dibutuhkan via Security(get_current_user, scopes=[...]).
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from app.api.deps import get_auth_service
from app.application.auth_service import AuthService, CurrentUser
from app.application.errors import InvalidToken

SCOPES = {
    "orders:write": "Membuat dan membayar order sendiri",
    "orders:all": "Mengelola order semua customer",
    "products:write": "Menambah dan mengubah produk",
    "reports:read": "Melihat report penjualan",
}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", scopes=SCOPES, auto_error=False)


def get_current_user(
    security_scopes: SecurityScopes,
    token: str | None = Depends(oauth2_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    if not token:
        raise InvalidToken("Butuh login: kirim header Authorization: Bearer <token>")
    return auth.authenticate(token, security_scopes.scopes)
