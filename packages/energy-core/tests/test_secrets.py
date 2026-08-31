"""Tests for encrypted secret storage."""

import os

import pytest
from cryptography.fernet import Fernet

from energy_core.secrets import CredentialCipher, SecretBox, SecretBoxError


def test_encrypt_decrypt_round_trip(monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    box = SecretBox.from_settings()
    encrypted = box.encrypt("super-secret-password")
    assert encrypted != "super-secret-password"
    assert box.decrypt(encrypted) == "super-secret-password"


def test_credential_cipher_round_trip(monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    cipher = CredentialCipher()
    encrypted = cipher.encrypt("integration-secret")
    assert encrypted != "integration-secret"
    assert cipher.decrypt(encrypted) == "integration-secret"


def test_empty_string_stays_empty(monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    box = SecretBox.from_settings()
    assert box.encrypt("") == ""
    assert box.decrypt("") == ""


def test_invalid_token_raises(monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    box = SecretBox.from_settings()
    with pytest.raises(SecretBoxError):
        box.decrypt("not-a-valid-token")


def test_key_persists_from_env(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    monkeypatch.delenv("EMIC_SECRET_KEY_PATH", raising=False)
    first = SecretBox.from_settings()
    second = SecretBox.from_settings()
    token = first.encrypt("refresh-token-value")
    assert second.decrypt(token) == "refresh-token-value"
