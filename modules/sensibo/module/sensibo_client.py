"""Sensibo HTTP client — GET/read operations only."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SENSIBO_API_BASE = "https://home.sensibo.com/api/v2"
ALLOWED_METHODS = frozenset({"GET", "HEAD"})


@dataclass(frozen=True, slots=True)
class SensiboRequestAudit:
    method: str
    path: str


class SensiboClientError(Exception):
    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class SensiboClient:
    """Read-only Sensibo API client using broker-supplied network transport."""

    def __init__(
        self,
        *,
        api_key: str,
        request_fn: Callable[..., dict[str, Any]],
        timeout: float = 10.0,
        max_retries: int = 2,
        audit_hook: Callable[[SensiboRequestAudit], None] | None = None,
    ) -> None:
        self._api_key = api_key
        self._request_fn = request_fn
        self._timeout = timeout
        self._max_retries = max_retries
        self._audit = audit_hook or (lambda _a: None)

    def list_pods(self) -> list[dict[str, Any]]:
        data = self._get_json("/users/me/pods")
        result = data.get("result") if isinstance(data, dict) else data
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        return []

    def get_pod(self, pod_id: str) -> dict[str, Any]:
        data = self._get_json(f"/pods/{pod_id}")
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            return data["result"]
        if isinstance(data, dict):
            return data
        return {}

    def get_measurements(self, pod_id: str, *, limit: int = 1) -> list[dict[str, Any]]:
        query = urlencode({"limit": str(limit)})
        data = self._get_json(f"/pods/{pod_id}/measurements?{query}")
        result = data.get("result") if isinstance(data, dict) else data
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        return []

    def _get_json(self, path: str) -> Any:
        url = f"{SENSIBO_API_BASE}{path}"
        self._audit(SensiboRequestAudit(method="GET", path=path))
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._request_fn(
                    url=url,
                    method="GET",
                    headers={
                        "X-API-KEY": self._api_key,
                        "Accept": "application/json",
                    },
                    timeout=self._timeout,
                )
                status = int(response.get("status_code") or 0)
                body = response.get("body") or ""
                if status in {401, 403}:
                    raise SensiboClientError("authentication failed", status=status, retryable=False)
                if status == 429:
                    if attempt < self._max_retries:
                        time.sleep(min(2 ** attempt, 8))
                        continue
                    raise SensiboClientError("rate limited", status=429, retryable=True)
                if status >= 500:
                    if attempt < self._max_retries:
                        time.sleep(min(2 ** attempt, 8))
                        continue
                    raise SensiboClientError("server error", status=status, retryable=True)
                if status >= 400:
                    raise SensiboClientError(f"request failed status={status}", status=status, retryable=False)
                if not body:
                    return {}
                return json.loads(body)
            except SensiboClientError:
                raise
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise SensiboClientError(str(exc), retryable=True) from exc
        raise SensiboClientError(str(last_error or "unknown error"), retryable=True)
