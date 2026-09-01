"""Extract ChargeFinder AES key from public web bundle."""

from __future__ import annotations

import re
import time

import httpx

_KEY_RE = re.compile(r'TextEncoder\)\.encode\("([0-9a-f]{16,64})"\)')
_BUNDLE_RE = re.compile(r'<script[^>]+src="(/js/[^"]+)"')

_cached_key: str | None = None
_cached_at: float = 0.0
_CACHE_TTL_SECONDS = 3600.0


def extract_aes_key_hex(*, timeout_seconds: float = 15.0, force_refresh: bool = False) -> str:
    global _cached_key, _cached_at
    now = time.monotonic()
    if not force_refresh and _cached_key is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_key

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        html = client.get("https://chargefinder.com/").text
        bundles = _BUNDLE_RE.findall(html)
        for bundle_path in bundles:
            js = client.get(f"https://chargefinder.com{bundle_path}").text
            match = _KEY_RE.search(js)
            if match:
                _cached_key = match.group(1)
                _cached_at = now
                return _cached_key
    raise RuntimeError("ChargeFinder AES key not found in web bundle")


def reset_key_cache() -> None:
    global _cached_key, _cached_at
    _cached_key = None
    _cached_at = 0.0
