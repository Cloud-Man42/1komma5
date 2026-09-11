"""RPC session authentication for isolated runtime."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class RuntimeSession:
    runtime_instance_id: str
    module_id: str
    site_id: int
    session_token: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    revoked: bool = False


class RuntimeSessionStore:
    def __init__(self, *, session_ttl_seconds: float = 3600.0) -> None:
        self._sessions: dict[str, RuntimeSession] = {}
        self._startup_tokens: dict[str, tuple[str, datetime]] = {}
        self._session_ttl = session_ttl_seconds
        self._secret = secrets.token_hex(32)

    def issue_startup_token(self, runtime_instance_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._startup_tokens[token] = (runtime_instance_id, datetime.now(UTC))
        return token

    def consume_startup_token(self, token: str, *, expected_instance_id: str) -> bool:
        entry = self._startup_tokens.pop(token, None)
        if entry is None:
            return False
        instance_id, issued_at = entry
        if instance_id != expected_instance_id:
            return False
        if datetime.now(UTC) - issued_at > timedelta(seconds=60):
            return False
        return True

    def create_session(
        self,
        *,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
    ) -> RuntimeSession:
        raw = secrets.token_urlsafe(32)
        token = self._sign(runtime_instance_id, raw)
        session = RuntimeSession(
            runtime_instance_id=runtime_instance_id,
            module_id=module_id,
            site_id=site_id,
            session_token=token,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._session_ttl),
        )
        self._sessions[token] = session
        return session

    def validate_session(
        self,
        token: str,
        *,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
    ) -> RuntimeSession | None:
        session = self._sessions.get(token)
        if session is None or session.revoked:
            return None
        if session.runtime_instance_id != runtime_instance_id:
            return None
        if session.module_id != module_id:
            return None
        if session.site_id != site_id:
            return None
        if session.expires_at and datetime.now(UTC) > session.expires_at:
            session.revoked = True
            return None
        return session

    def revoke_runtime(self, runtime_instance_id: str) -> None:
        for session in self._sessions.values():
            if session.runtime_instance_id == runtime_instance_id:
                session.revoked = True

    def has_active_session(self, runtime_instance_id: str) -> bool:
        now = datetime.now(UTC)
        for session in self._sessions.values():
            if session.revoked:
                continue
            if session.runtime_instance_id != runtime_instance_id:
                continue
            if session.expires_at and now > session.expires_at:
                continue
            return True
        return False

    def _sign(self, runtime_instance_id: str, raw: str) -> str:
        digest = hmac.new(
            self._secret.encode("utf-8"),
            f"{runtime_instance_id}:{raw}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{raw}.{digest}"
