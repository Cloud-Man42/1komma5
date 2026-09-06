"""Track sites that need snapshot refresh after domain events."""

from __future__ import annotations

from threading import Lock

_dirty_site_ids: set[int] = set()
_lock = Lock()


def mark_site_dirty(site_id: int) -> None:
    with _lock:
        _dirty_site_ids.add(site_id)


def drain_dirty_site_ids() -> set[int]:
    with _lock:
        drained = set(_dirty_site_ids)
        _dirty_site_ids.clear()
        return drained


def reset_dirty_sites() -> None:
    with _lock:
        _dirty_site_ids.clear()
