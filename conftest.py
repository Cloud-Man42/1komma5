"""Repo-wide test guards."""

from __future__ import annotations

import pytest


class OutboundNetworkBlocked(RuntimeError):
    """A test tried to reach a live service instead of a fake."""


def _message(url: object) -> str:
    return (
        f"Outbound request to {url} blocked. Mock the client or provider instead, "
        "or mark the test with @pytest.mark.integration if it truly needs the network."
    )


@pytest.fixture(autouse=True)
def block_outbound_http(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail fast on real HTTP calls so a networkless runner cannot be the first to notice.

    Only the transports that open sockets are patched, so httpx ASGITransport and
    MockTransport keep working for in-process API tests.
    """
    if "integration" in request.keywords:
        return

    def blocked_httpx(_self: object, http_request: object, *_args: object, **_kwargs: object):
        raise OutboundNetworkBlocked(_message(getattr(http_request, "url", "unknown URL")))

    monkeypatch.setattr("httpx.AsyncHTTPTransport.handle_async_request", blocked_httpx)
    monkeypatch.setattr("httpx.HTTPTransport.handle_request", blocked_httpx)

    try:
        import requests.adapters
    except ImportError:
        return

    def blocked_requests(_self: object, prepared: object, *_args: object, **_kwargs: object):
        raise OutboundNetworkBlocked(_message(getattr(prepared, "url", "unknown URL")))

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", blocked_requests)
