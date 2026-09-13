"""Per-account token refresh locks — prevent cross-account refresh races."""

from __future__ import annotations

import asyncio

_refresh_locks: dict[int, asyncio.Lock] = {}


def refresh_lock_for(account_id: int) -> asyncio.Lock:
    lock = _refresh_locks.get(account_id)
    if lock is None:
        lock = asyncio.Lock()
        _refresh_locks[account_id] = lock
    return lock


def clear_refresh_locks_for_tests() -> None:
    _refresh_locks.clear()
