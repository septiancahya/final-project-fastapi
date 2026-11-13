"""Exception khusus auth/otorisasi di layer application."""


class InvalidCredentials(Exception):
    """Email atau password salah"""


class InvalidToken(Exception):
    """Token tidak ada, palsu, atau kedaluwarsa."""


class AccessDenied(Exception):
    """Sudah login tapi tidak punya scope / bukan pemilik resource."""


class UserAlreadyExists(Exception):
    """Email sudah terdaftar saat register."""


class TooManyLoginAttempts(Exception):
    """Login diblokir sementara karena terlalu banyak gagal."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Terlalu banyak percobaan login, coba lagi dalam {retry_after} detik")
