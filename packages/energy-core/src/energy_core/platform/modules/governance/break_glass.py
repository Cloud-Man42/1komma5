"""Break-glass session store (Step 5C.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from energy_core.platform.modules.governance.types import BreakGlassSession


class BreakGlassStore:
    """Process-local break-glass sessions with expiry."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._session: BreakGlassSession | None = None

    def activate(self, *, reason: str, expires_at: datetime, actor: str) -> BreakGlassSession:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        session = BreakGlassSession(reason=reason, expires_at=expires_at, actor=actor)
        with self._lock:
            self._session = session
        return session

    def clear(self) -> None:
        with self._lock:
            self._session = None

    def current(self) -> BreakGlassSession | None:
        with self._lock:
            session = self._session
        if session is None:
            return None
        now = datetime.now(UTC)
        expires = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=UTC)
        if expires <= now:
            self.clear()
            return None
        return session

    def is_active(self) -> bool:
        return self.current() is not None


_default_store = BreakGlassStore()


def get_break_glass_store() -> BreakGlassStore:
    return _default_store
