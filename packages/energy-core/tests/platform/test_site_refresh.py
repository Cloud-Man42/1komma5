"""Tests for dirty-site snapshot refresh registry."""

from __future__ import annotations

from energy_core.platform.events.site_refresh import (
    drain_dirty_site_ids,
    mark_site_dirty,
    reset_dirty_sites,
)


def test_mark_and_drain_dirty_sites():
    reset_dirty_sites()
    mark_site_dirty(1)
    mark_site_dirty(2)
    mark_site_dirty(1)
    drained = drain_dirty_site_ids()
    assert drained == {1, 2}
    assert drain_dirty_site_ids() == set()


def test_reset_dirty_sites():
    mark_site_dirty(9)
    reset_dirty_sites()
    assert drain_dirty_site_ids() == set()
