"""Decrypt ChargeFinder AES-GCM + zlib API responses."""

from __future__ import annotations

import json
import zlib
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def is_encrypted(data: Any) -> bool:
    return isinstance(data, dict) and {"i", "e", "a"}.issubset(data.keys())


def decrypt_response(key: bytes, data: dict[str, str]) -> dict | list:
    iv = bytes.fromhex(data["i"])
    ciphertext = bytes.fromhex(data["e"])
    auth_tag = bytes.fromhex(data["a"])
    decrypted = AESGCM(key).decrypt(iv, ciphertext + auth_tag, None)
    if decrypted[:1] == b"\x78":
        decompressed = zlib.decompress(decrypted, zlib.MAX_WBITS)
    else:
        decompressed = zlib.decompress(decrypted, -zlib.MAX_WBITS)
    return json.loads(decompressed.decode("utf-8"))
