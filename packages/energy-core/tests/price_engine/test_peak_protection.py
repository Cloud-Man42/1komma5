"""Tests for fuse peak-protection hints."""

from energy_core.price_engine.peak_protection import assess_peak_protection


def test_peak_protection_when_fuse_near_capacity():
    hint = assess_peak_protection(
        main_fuse_a=25.0,
        grid_import_w=16_000.0,
        headroom_threshold_a=4.0,
        utilization_threshold_pct=85.0,
    )
    assert hint is not None
    assert hint.utilization_pct >= 85.0
    assert hint.fuse_headroom_a is not None
    assert hint.fuse_headroom_a <= 4.0
    assert "Huvudsäkring" in hint.reason_sv


def test_peak_protection_none_when_headroom_ok():
    hint = assess_peak_protection(main_fuse_a=25.0, grid_import_w=2_000.0)
    assert hint is None


def test_peak_protection_none_without_fuse_or_import():
    assert assess_peak_protection(main_fuse_a=None, grid_import_w=10_000.0) is None
    assert assess_peak_protection(main_fuse_a=25.0, grid_import_w=None) is None
