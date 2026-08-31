"""Tests for Mercedes error classification."""

from __future__ import annotations

import httpx
import pytest

from energy_core.vehicles.mercedes.errors import MercedesErrorCode, classify_exception, classify_http_status


def test_classify_http_401():
    error = classify_http_status(401, endpoint="/v2/vehicles")
    assert error.code == MercedesErrorCode.TOKEN_EXPIRED
    assert error.retryable is True


def test_classify_http_429():
    error = classify_http_status(429)
    assert error.code == MercedesErrorCode.RATE_LIMITED


def test_classify_timeout():
    error = classify_exception(httpx.ReadTimeout("timeout"), endpoint="/v1/config")
    assert error.code == MercedesErrorCode.TIMEOUT
