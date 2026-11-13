"""User yang bisa login beserta aturan RBAC-nya.

ROLE_SCOPES adalah satu-satunya sumber kebenaran role -> scope. Scope tidak
disimpan di database; cukup role pada baris user, scope-nya diturunkan di sini.
"""
from dataclasses import dataclass

ROLE_SCOPES = {
    "customer": {"orders:write"},
    "admin": {"orders:write", "orders:all", "products:write", "reports:read"},
}


@dataclass
class User:
    email: str
    password_hash: str
    role: str = "customer"
    id: int | None = None

    def __post_init__(self) -> None:
        if self.role not in ROLE_SCOPES:
            raise ValueError(f"Role {self.role} tidak dikenal")

    @property
    def scopes(self) -> set[str]:
        return ROLE_SCOPES[self.role]
