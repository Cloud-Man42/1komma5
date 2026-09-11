"""Per-module package mutation lock."""

from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path

from energy_core.platform.modules.packages.errors import PackageError

PACKAGE_LOCKED = "PACKAGE_LOCKED"


class PackageMutationLock:
    _memory_locks: dict[str, threading.Lock] = {}
    _guard = threading.Lock()

    def __init__(self, modules_root: str | Path) -> None:
        self._root = Path(modules_root)

    @classmethod
    def _lock_for(cls, module_id: str) -> threading.Lock:
        with cls._guard:
            lock = cls._memory_locks.get(module_id)
            if lock is None:
                lock = threading.Lock()
                cls._memory_locks[module_id] = lock
            return lock

    @contextlib.contextmanager
    def acquire(self, module_id: str, *, timeout_seconds: float = 30.0):
        lock = self._lock_for(module_id)
        acquired = lock.acquire(timeout=timeout_seconds)
        if not acquired:
            raise PackageError(f"package mutation locked: {module_id}", code=PACKAGE_LOCKED)
        lock_dir = self._root / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / f"{module_id}.lock"
        lock_file.write_text(str(time.time()), encoding="utf-8")
        try:
            yield
        finally:
            lock_file.unlink(missing_ok=True)
            lock.release()
