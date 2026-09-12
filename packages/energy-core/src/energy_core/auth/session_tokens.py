"""Session and CSRF token generation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

SESSION_PREFIX = "es_"
SESSION_BYTE_LENGTH = 32
LOOKUP_PREFIX_LENGTH = 12


@dataclass(frozen=True, slots=True)
class GeneratedSessionToken:
    token: str
    token_prefix: str
    token_hash: str


def generate_session_token() -> GeneratedSessionToken:
    raw = secrets.token_urlsafe(SESSION_BYTE_LENGTH)
    token = f"{SESSION_PREFIX}{raw}"
    return GeneratedSessionToken(
        token=token,
        token_prefix=token[:LOOKUP_PREFIX_LENGTH],
        token_hash=hash_token(token),
    )


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)


def extract_session_prefix(token: str) -> str | None:
    if not token.startswith(SESSION_PREFIX) or len(token) < LOOKUP_PREFIX_LENGTH:
        return None
    return token[:LOOKUP_PREFIX_LENGTH]
