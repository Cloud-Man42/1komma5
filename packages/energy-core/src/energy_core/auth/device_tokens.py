"""Device token generation and verification for Apple widget clients."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass


TOKEN_PREFIX = "emic_"
TOKEN_BYTE_LENGTH = 32
LOOKUP_PREFIX_LENGTH = 12


@dataclass(frozen=True, slots=True)
class GeneratedDeviceToken:
    token: str
    token_prefix: str
    token_hash: str


def generate_device_token() -> GeneratedDeviceToken:
    """Create a new opaque device token and its stored hash."""
    raw = secrets.token_urlsafe(TOKEN_BYTE_LENGTH)
    token = f"{TOKEN_PREFIX}{raw}"
    return GeneratedDeviceToken(
        token=token,
        token_prefix=token[:LOOKUP_PREFIX_LENGTH],
        token_hash=hash_token(token),
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(token: str, stored_hash: str) -> bool:
    expected = hash_token(token)
    return hmac.compare_digest(expected, stored_hash)


def extract_lookup_prefix(token: str) -> str | None:
    if not token.startswith(TOKEN_PREFIX) or len(token) < LOOKUP_PREFIX_LENGTH:
        return None
    return token[:LOOKUP_PREFIX_LENGTH]
