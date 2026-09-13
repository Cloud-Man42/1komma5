"""Password hashing for EMIC users (Argon2 via pwdlib)."""

from __future__ import annotations

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_hasher = PasswordHash((Argon2Hasher(),))

MAX_PASSWORD_LENGTH = 128


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def validate_password_policy(password: str) -> str | None:
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Lösenordet får vara högst {MAX_PASSWORD_LENGTH} tecken."
    if not password.strip():
        return "Lösenordet får inte vara tomt."
    return None
