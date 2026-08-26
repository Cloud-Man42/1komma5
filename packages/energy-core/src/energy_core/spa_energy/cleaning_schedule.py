"""Daily spa cleaning schedule planning and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.types import EnergySource, LoadStrategy, PlanWindow, ScoredBlock
from energy_core.spa_energy.requirement import CLEANING_STATUSES


INTERVAL_MINUTES = 15
START_COUNT_PENALTY = 500.0


@dataclass(frozen=True, slots=True)
class CleaningConfigValidation:
    feasible: bool
    warning_sv: str | None = None
    max_achievable_hours: float | None = None


@dataclass(frozen=True, slots=True)
class CleaningDailyProgress:
    completed_hours: float
    target_hours: float
    progress_pct: float
    starts_used: int


def allowed_window_hours(start_hhmm: str, end_hhmm: str) -> float:
    sh, sm = (int(x) for x in start_hhmm.split(":"))
    eh, em = (int(x) for x in end_hhmm.split(":"))
    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    return (end_minutes - start_minutes) / 60.0


def validate_cleaning_config(
    *,
    daily_hours: float,
    min_cycle_minutes: int,
    min_pause_minutes: int,
    max_starts: int,
    allowed_start: str,
    allowed_end: str,
) -> CleaningConfigValidation:
    min_cycle_hours = min_cycle_minutes / 60.0
    window_hours = allowed_window_hours(allowed_start, allowed_end)

    if min_cycle_hours > window_hours:
        return CleaningConfigValidation(
            feasible=False,
            warning_sv=(
                f"Minsta cleaning-cykel ({min_cycle_minutes} min) är längre än tillåtet tidsfönster "
                f"({allowed_start}–{allowed_end}). Minska minsta cykellängd eller utöka tidsfönstret."
            ),
            max_achievable_hours=min(daily_hours, max_starts * window_hours),
        )

    feasible = False
    max_achievable = 0.0
    for starts in range(1, max_starts + 1):
        hours_per_start = daily_hours / starts
        achievable = min(daily_hours, starts * window_hours)
        max_achievable = max(max_achievable, achievable)
        if hours_per_start + 1e-9 >= min_cycle_hours and daily_hours <= starts * window_hours + 1e-9:
            feasible = True
            break

    if not feasible:
        min_starts_needed = next(
            (
                starts
                for starts in range(1, 9)
                if daily_hours / starts + 1e-9 >= min_cycle_hours
                and daily_hours <= starts * window_hours + 1e-9
            ),
            max_starts + 1,
        )
        return CleaningConfigValidation(
            feasible=False,
            warning_sv=(
                f"Inställningarna kan inte garantera {daily_hours:g} timmars cleaning per dygn. "
                f"Öka max antal starter (behövs minst {min_starts_needed}) eller ändra minsta cykellängd."
            ),
            max_achievable_hours=max_achievable,
        )

    return CleaningConfigValidation(feasible=True, max_achievable_hours=max_achievable)


def build_config_summary_sv(
    *,
    daily_hours: float,
    min_cycle_minutes: int,
    max_starts: int,
    allowed_start: str,
    allowed_end: str,
) -> str:
    return (
        f"EMIC ska köra totalt {daily_hours:g} timmar cleaning per dygn, "
        f"fördelat på högst {max_starts} starter mellan {allowed_start} och {allowed_end}. "
        f"Varje körning blir minst {min_cycle_minutes} minuter."
    )


def build_filter_plan_summary_sv(
    *,
    cycles_per_day: int,
    duration_minutes: int,
    allowed_start: str,
    allowed_end: str,
) -> str:
    total_hours = cycles_per_day * duration_minutes / 60.0
    cycle_hours = duration_minutes // 60
    return (
        f"Arctic Spa grundschema: {cycles_per_day} cykler per dygn, "
        f"{cycle_hours} h per cykel ({total_hours:g} h totalt) mellan {allowed_start} och {allowed_end}."
    )


def compute_cleaning_hours_today(
    samples: list[tuple[datetime, str | None]],
    *,
    day_start: datetime,
    day_end: datetime,
) -> tuple[float, int]:
    """Return (completed_hours, starts_count) for the local day."""
    if not samples:
        return 0.0, 0

    sorted_samples = sorted(samples, key=lambda x: x[0])
    total_seconds = 0.0
    starts = 0
    in_cleaning = False
    segment_start: datetime | None = None

    for ts, status in sorted_samples:
        if ts < day_start:
            active = status in CLEANING_STATUSES
            in_cleaning = active
            if active:
                segment_start = day_start
            continue
        if ts > day_end:
            break

        active = status in CLEANING_STATUSES
        if active and not in_cleaning:
            in_cleaning = True
            segment_start = ts
            starts += 1
        elif not active and in_cleaning and segment_start is not None:
            total_seconds += (ts - max(segment_start, day_start)).total_seconds()
            in_cleaning = False
            segment_start = None

    if in_cleaning and segment_start is not None:
        total_seconds += (min(day_end, sorted_samples[-1][0]) - max(segment_start, day_start)).total_seconds()

    return max(0.0, total_seconds / 3600.0), starts


def compute_daily_progress(completed_hours: float, target_hours: float) -> CleaningDailyProgress:
    target = max(target_hours, 0.01)
    pct = min(100.0, round(100.0 * completed_hours / target, 1))
    return CleaningDailyProgress(
        completed_hours=round(completed_hours, 2),
        target_hours=target_hours,
        progress_pct=pct,
        starts_used=0,
    )


def _window_from_blocks(
    window_blocks: tuple[ScoredBlock, ...],
    *,
    nominal_power_w: float,
) -> PlanWindow:
    start = window_blocks[0].block.timestamp
    end = window_blocks[-1].block.timestamp + timedelta(minutes=INTERVAL_MINUTES)
    length = len(window_blocks)
    energy_kwh = (nominal_power_w / 1000.0) * (length * INTERVAL_MINUTES / 60.0)
    cost = sum(
        b.marginal_cost_sek_kwh * (nominal_power_w / 1000.0) * (INTERVAL_MINUTES / 60.0)
        for b in window_blocks
    )
    sources = [b.expected_energy_source for b in window_blocks]
    primary = max(set(sources), key=sources.count)
    score = sum(b.score for b in window_blocks) / len(window_blocks)
    return PlanWindow(
        start=start,
        end=end,
        duration=end - start,
        expected_energy_kwh=energy_kwh,
        expected_cost_sek=cost,
        expected_energy_source=primary,
        average_score=score,
        blocks=window_blocks,
    )


def _block_score_for_strategy(
    window_blocks: tuple[ScoredBlock, ...],
    strategy: LoadStrategy,
    nominal_power_w: float,
) -> float:
    if strategy == LoadStrategy.SOLAR_ONLY:
        avg_surplus = sum(b.block.available_surplus_w for b in window_blocks) / len(window_blocks)
        if avg_surplus < nominal_power_w * 0.5:
            return float("-inf")
    if strategy == LoadStrategy.CHEAPEST:
        return -sum(b.marginal_cost_sek_kwh for b in window_blocks) / len(window_blocks)
    return sum(b.score for b in window_blocks) / len(window_blocks)


def _find_best_window_at_index(
    scored: tuple[ScoredBlock, ...],
    start_idx: int,
    blocks_needed: int,
    strategy: LoadStrategy,
    nominal_power_w: float,
) -> PlanWindow | None:
    if start_idx + blocks_needed > len(scored):
        return None
    window_blocks = scored[start_idx : start_idx + blocks_needed]
    if strategy == LoadStrategy.SOLAR_ONLY:
        avg_surplus = sum(b.block.available_surplus_w for b in window_blocks) / len(window_blocks)
        if avg_surplus < nominal_power_w * 0.5:
            return None
    return _window_from_blocks(window_blocks, nominal_power_w=nominal_power_w)


def _merge_windows(
    windows: list[PlanWindow],
    *,
    min_pause: timedelta,
    max_merged_hours: float,
    nominal_power_w: float,
) -> list[PlanWindow]:
    if len(windows) < 2:
        return windows

    merged: list[PlanWindow] = []
    current = windows[0]
    for nxt in windows[1:]:
        gap = nxt.start - current.end
        merged_hours = (nxt.end - current.start).total_seconds() / 3600.0
        if gap <= min_pause and merged_hours <= max_merged_hours:
            combined_blocks = current.blocks + nxt.blocks
            current = _window_from_blocks(combined_blocks, nominal_power_w=nominal_power_w)
        else:
            merged.append(current)
            current = nxt
    merged.append(current)
    return merged


def _enumerate_fixed_cycle_plans(
    candidates: list[PlanWindow],
    *,
    cycles_needed: int,
    min_separation: timedelta,
) -> tuple[PlanWindow, ...]:
    best: tuple[PlanWindow, ...] = ()
    best_score = float("-inf")

    def compatible(chosen: list[PlanWindow], candidate: PlanWindow) -> bool:
        if not chosen:
            return True
        return candidate.start >= chosen[-1].end + min_separation

    def backtrack(start_idx: int, chosen: list[PlanWindow]) -> None:
        nonlocal best, best_score
        if len(chosen) == cycles_needed:
            score = sum(w.average_score for w in chosen)
            if score > best_score:
                best_score = score
                best = tuple(chosen)
            return
        remaining = cycles_needed - len(chosen)
        if start_idx >= len(candidates) or len(candidates) - start_idx < remaining:
            return
        for idx in range(start_idx, len(candidates)):
            candidate = candidates[idx]
            if not compatible(chosen, candidate):
                continue
            backtrack(idx + 1, [*chosen, candidate])

    backtrack(0, [])
    return best


def plan_fixed_filter_cycles(
    scored: tuple[ScoredBlock, ...],
    *,
    cycles_per_day: int,
    duration_minutes: int,
    min_separation: timedelta,
    earliest: datetime,
    latest: datetime,
    now: datetime,
    strategy: LoadStrategy,
    nominal_power_w: float,
) -> tuple[PlanWindow, ...]:
    """Plan exactly N contiguous cycles of fixed duration — never split or merge."""
    if not scored or cycles_per_day <= 0 or duration_minutes <= 0:
        return ()

    blocks_per_cycle = max(1, duration_minutes // INTERVAL_MINUTES)
    if blocks_per_cycle * INTERVAL_MINUTES != duration_minutes:
        blocks_per_cycle = max(1, int(round(duration_minutes / INTERVAL_MINUTES)))

    eligible = tuple(
        s
        for s in scored
        if earliest <= s.block.timestamp < latest
        and s.block.timestamp >= now - timedelta(minutes=INTERVAL_MINUTES)
        and s.load_feasible
    )
    if not eligible:
        eligible = tuple(s for s in scored if earliest <= s.block.timestamp < latest)

    seen: set[tuple[datetime, datetime]] = set()
    candidates: list[PlanWindow] = []
    for start_idx in range(len(eligible) - blocks_per_cycle + 1):
        window = _find_best_window_at_index(
            eligible,
            start_idx,
            blocks_per_cycle,
            strategy,
            nominal_power_w,
        )
        if window is None:
            continue
        key = (window.start, window.end)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(window)

    if not candidates:
        return ()

    candidates.sort(key=lambda w: w.start)
    plan = _enumerate_fixed_cycle_plans(
        candidates,
        cycles_needed=cycles_per_day,
        min_separation=min_separation,
    )
    if plan:
        return plan

    # Fallback: evenly spaced windows within eligible horizon (still exact duration)
    if len(eligible) >= blocks_per_cycle:
        step = max(1, (len(eligible) - blocks_per_cycle) // max(1, cycles_per_day))
        fallback: list[PlanWindow] = []
        idx = 0
        while len(fallback) < cycles_per_day and idx + blocks_per_cycle <= len(eligible):
            window = _find_best_window_at_index(
                eligible,
                idx,
                blocks_per_cycle,
                strategy,
                nominal_power_w,
            )
            if window and (not fallback or window.start >= fallback[-1].end + min_separation):
                fallback.append(window)
            idx += step
        if len(fallback) == cycles_per_day:
            return tuple(fallback)

    return ()


def plan_daily_cleaning_windows(
    scored: tuple[ScoredBlock, ...],
    *,
    daily_hours: float,
    min_cycle: timedelta,
    min_pause: timedelta,
    max_starts: int,
    earliest: datetime,
    latest: datetime,
    now: datetime,
    strategy: LoadStrategy,
    nominal_power_w: float,
) -> tuple[PlanWindow, ...]:
    """Plan one or more cleaning windows that sum to daily_hours, minimizing starts."""
    if not scored or daily_hours <= 0 or max_starts <= 0:
        return ()

    eligible = tuple(
        s
        for s in scored
        if earliest <= s.block.timestamp < latest
        and s.block.timestamp >= now - timedelta(minutes=INTERVAL_MINUTES)
        and s.load_feasible
    )
    if not eligible:
        eligible = tuple(s for s in scored if earliest <= s.block.timestamp < latest)

    min_blocks = max(1, int(min_cycle.total_seconds() / (INTERVAL_MINUTES * 60)))
    daily_blocks = max(min_blocks, int(round(daily_hours * 60 / INTERVAL_MINUTES)))

    best_windows: tuple[PlanWindow, ...] = ()
    best_score = float("-inf")

    for num_starts in range(1, max_starts + 1):
        blocks_per_window = max(min_blocks, int(round(daily_blocks / num_starts)))
        total_blocks = blocks_per_window * num_starts
        if total_blocks < daily_blocks:
            blocks_per_window += 1
            total_blocks = blocks_per_window * num_starts

        hours_per_window = blocks_per_window * INTERVAL_MINUTES / 60.0
        if hours_per_window < min_cycle.total_seconds() / 3600.0:
            continue

        pause_blocks = max(1, int(min_pause.total_seconds() / (INTERVAL_MINUTES * 60)))
        windows: list[PlanWindow] = []
        used_until = -1

        for _ in range(num_starts):
            best: PlanWindow | None = None
            best_local = float("-inf")
            for start_idx in range(used_until + 1, len(eligible) - blocks_per_window + 1):
                candidate = _find_best_window_at_index(
                    eligible,
                    start_idx,
                    blocks_per_window,
                    strategy,
                    nominal_power_w,
                )
                if candidate is None:
                    continue
                local_score = _block_score_for_strategy(candidate.blocks, strategy, nominal_power_w)
                if local_score > best_local:
                    best_local = local_score
                    best = candidate
            if best is None:
                windows = []
                break
            windows.append(best)
            end_idx = eligible.index(best.blocks[-1])
            used_until = end_idx + pause_blocks

        if not windows:
            continue

        merged = _merge_windows(
            windows,
            min_pause=min_pause,
            max_merged_hours=daily_hours + 0.01,
            nominal_power_w=nominal_power_w,
        )
        actual_starts = len(merged)
        energy_score = sum(w.average_score for w in merged)
        plan_score = energy_score - START_COUNT_PENALTY * actual_starts

        if plan_score > best_score:
            best_score = plan_score
            best_windows = tuple(merged)

    if best_windows:
        return best_windows

    # Fallback: single best contiguous window up to daily_blocks
    fallback_blocks = min(daily_blocks, len(eligible))
    fallback_blocks = max(min_blocks, fallback_blocks)
    best: PlanWindow | None = None
    best_local = float("-inf")
    for start_idx in range(len(eligible) - fallback_blocks + 1):
        candidate = _find_best_window_at_index(
            eligible,
            start_idx,
            fallback_blocks,
            strategy,
            nominal_power_w,
        )
        if candidate is None:
            continue
        local_score = _block_score_for_strategy(candidate.blocks, strategy, nominal_power_w)
        if local_score > best_local:
            best_local = local_score
            best = candidate
    return (best,) if best else ()


def energy_source_label_sv(source: EnergySource, solar_share: float | None = None) -> str:
    if solar_share is not None and solar_share >= 0.85:
        return f"☀ {int(round(solar_share * 100))} % solel"
    if source == EnergySource.SOLAR:
        return "☀ Solel"
    if source == EnergySource.BATTERY:
        return "🔋 Batteri"
    if source == EnergySource.MIXED:
        return "🔋 Batteri + sol"
    return "⚡ Nät"
