"""Sanitize untrusted publisher/module content for Store display."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_EVENT_HANDLER_RE = re.compile(r"\s+on\w+\s*=", re.IGNORECASE)
_JAVASCRIPT_URL_RE = re.compile(r"javascript\s*:", re.IGNORECASE)
_MAX_TEXT_LEN = 8000


def sanitize_text(value: str | None, *, max_len: int = _MAX_TEXT_LEN) -> str:
    if not value:
        return ""
    text = html.unescape(str(value))
    text = _SCRIPT_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    text = _EVENT_HANDLER_RE.sub(" ", text)
    text = _JAVASCRIPT_URL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def sanitize_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in {"https"}:
        return None
    if not parsed.netloc:
        return None
    return parsed.geturl()
