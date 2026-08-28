"""Tests for Arctic Spa fixed filter policy."""

from energy_core.spa_energy.filter_policy import SpaFilterPolicy, is_spa_filter_self_managed

def test_default_policy_is_four_by_two_hours():
    policy = SpaFilterPolicy()
    assert policy.cycles_per_day == 4
    assert policy.duration_per_cycle_minutes == 120
    assert policy.total_daily_runtime_hours == 8.0


def test_policy_validation_feasible_in_default_window():
    policy = SpaFilterPolicy()
    result = policy.validate()
    assert result.feasible is True


def test_policy_validation_infeasible_window():
    policy = SpaFilterPolicy(earliest_start="07:00", latest_finish="12:00")
    result = policy.validate()
    assert result.feasible is False
    assert result.warning_sv is not None


def test_sync_legacy_fields():
    policy = SpaFilterPolicy()
    synced = policy.sync_legacy_control_fields()
    assert synced["min_cleaning_hours_per_day"] == 8.0
    assert synced["max_starts_per_day"] == 4
    assert synced["min_run_minutes"] == 120
    assert synced["safety_floor_frequency_per_day"] == 4.0


def test_self_managed_when_optimization_disabled():
    class Control:
        filter_optimization_enabled = False
        strategy = "SMART"
        fixed_schedule_start = None
        fixed_schedule_end = None

    assert is_spa_filter_self_managed(Control()) is True


def test_self_managed_when_fixed_schedule_complete():
    class Control:
        filter_optimization_enabled = True
        strategy = "FIXED_SCHEDULE"
        fixed_schedule_start = "07:00"
        fixed_schedule_end = "22:00"

    assert is_spa_filter_self_managed(Control()) is True


def test_not_self_managed_when_fixed_schedule_incomplete():
    class Control:
        filter_optimization_enabled = True
        strategy = "FIXED_SCHEDULE"
        fixed_schedule_start = None
        fixed_schedule_end = "22:00"

    assert is_spa_filter_self_managed(Control()) is False
