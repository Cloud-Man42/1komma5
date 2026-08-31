"""Encrypted secret storage for integration credentials."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

DEFAULT_SECRET_KEY_PATH = Path("./emic-secret.key")


class SecretBoxError(RuntimeError):
    """Secret storage is unavailable or misconfigured."""


class SecretBox:
    """Encrypt and decrypt short strings at rest using Fernet."""

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    @classmethod
    def from_settings(cls) -> SecretBox:
        key = _resolve_key()
        return cls(key)

    @property
    def is_configured(self) -> bool:
        return True

    def encrypt(self, value: str) -> str:
        if value == "":
            return ""
        token = self._fernet.encrypt(value.encode("utf-8"))
        return token.decode("ascii")

    def decrypt(self, token: str) -> str:
        if token == "":
            return ""
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise SecretBoxError("Stored secret could not be decrypted") from exc


def _resolve_key() -> bytes:
    env_key = os.environ.get("EMIC_SECRET_KEY", "").strip()
    if env_key:
        return _normalize_key(env_key)

    key_path = Path(os.environ.get("EMIC_SECRET_KEY_PATH", DEFAULT_SECRET_KEY_PATH))
    if key_path.exists():
        return _normalize_key(key_path.read_text(encoding="utf-8").strip())

    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(key.decode("ascii"), encoding="utf-8")
    logger.warning(
        "Generated EMIC secret key at %s. Set EMIC_SECRET_KEY in production.",
        key_path.resolve(),
    )
    return key


def _normalize_key(raw: str) -> bytes:
    try:
        return raw.encode("ascii")
    except UnicodeEncodeError as exc:
        raise SecretBoxError("EMIC secret key must be ASCII Fernet key material") from exc


_FERNET_PREFIX = "gAAAA"


class CredentialCipher:
    """Encrypt integration credentials at rest with legacy plaintext fallback."""

    def __init__(self, secret_box: SecretBox | None = None) -> None:
        self._box = secret_box or SecretBox.from_settings()

    def encrypt(self, value: str) -> str:
        if value == "":
            return ""
        if value.startswith(_FERNET_PREFIX):
            try:
                self._box.decrypt(value)
                return value
            except SecretBoxError:
                pass
        return self._box.encrypt(value)

    def decrypt(self, stored: str) -> str:
        if stored == "":
            return ""
        if not stored.startswith(_FERNET_PREFIX):
            return stored
        try:
            return self._box.decrypt(stored)
        except SecretBoxError:
            return stored

    @staticmethod
    def is_configured(stored: str | None) -> bool:
        return bool(stored and stored.strip())
