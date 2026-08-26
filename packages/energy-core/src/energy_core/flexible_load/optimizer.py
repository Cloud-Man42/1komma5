"""Flexible load window optimizer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.deadline import compute_deadline_urgency
from energy_core.flexible_load.pricing import compute_block_load_cost
from energy_core.flexible_load.scoring import DEFAULT_WEIGHTS, score_block
from energy_core.flexible_load.types import (
    EnergySource,
    FlexibleLoad,
    HorizonBlock,
    LoadPlan,
    LoadStrategy,
    PlanWindow,
    ScoredBlock,
)
from energy_core.spa_energy.cleaning_schedule import plan_daily_cleaning_windows, plan_fixed_filter_cycles


class FlexibleLoadOptimizer:
    """Select optimal contiguous run windows for a flexible load."""

    def __init__(
        self,
        *,
        allow_battery: bool = True,
        prefer_solar: bool = True,
        min_battery_soc_pct: float = 40.0,
        fallback_price_sek_kwh: float = 2.0,
    ) -> None:
        self._allow_battery = allow_battery
        self._prefer_solar = prefer_solar
        self._min_battery_soc_pct = min_battery_soc_pct
        self._fallback_price_sek_kwh = fallback_price_sek_kwh

    def plan(
        self,
        load: FlexibleLoad,
        horizon: tuple[HorizonBlock, ...],
        strategy: LoadStrategy,
        *,
        now: datetime | None = None,
    ) -> LoadPlan:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        urgency = compute_deadline_urgency(now, load.deadline)
        scored = self._score_horizon(load, horizon, urgency)
        eligible = self._filter_eligible_blocks(scored, load, now)

        effective_strategy = strategy
        fallback_from_solar = False
        if strategy == LoadStrategy.SOLAR_ONLY and urgency.tier in {"critical", "urgent"}:
            effective_strategy = LoadStrategy.SMART
            fallback_from_solar = True

        if strategy == LoadStrategy.FIXED_SCHEDULE and load.fixed_start and load.fixed_end:
            window = self._window_from_fixed(load, scored, eligible)
            alt = self._best_window(load, eligible, LoadStrategy.SMART, urgency, now)
            return self._build_plan(
                load,
                strategy=strategy,
                windows=(window,) if window else (),
                scored=scored,
                reason="fixed_schedule",
                reason_sv="fast_schema",
                explanation_sv=self._explain_fixed(window, alt),
                fallback_from_solar=False,
                fixed_schedule_analysis=True,
                alternative_windows=(alt,) if alt else (),
            )

        if load.fixed_cycles_per_day is not None and load.fixed_cycle_duration is not None:
            return self._plan_fixed_filter_cycles(
                load, scored, eligible, strategy, urgency, now, fallback_from_solar
            )

        if load.daily_runtime_target is not None and load.max_starts_per_day:
            return self._plan_daily_cleaning(load, scored, eligible, strategy, urgency, now, fallback_from_solar)

        window = self._best_window(load, eligible, effective_strategy, urgency, now)
        if window is None and load.safety_critical:
            window = self._fallback_window(load, scored, now)

        reason, reason_sv = self._resolve_reason(window, effective_strategy, fallback_from_solar, urgency)
        explanation = self._explain_window(window, effective_strategy, fallback_from_solar)

        baseline = self._baseline_cost(load, scored)
        planned = window.expected_cost_sek if window else None
        savings = (baseline - planned) if baseline is not None and planned is not None else None

        return self._build_plan(
            load,
            strategy=strategy,
            windows=(window,) if window else (),
            scored=scored,
            reason=reason,
            reason_sv=reason_sv,
            explanation_sv=explanation,
            fallback_from_solar=fallback_from_solar,
            baseline_cost_sek=baseline,
            planned_cost_sek=planned,
            savings_sek=savings,
        )

    def _score_horizon(
        self,
        load: FlexibleLoad,
        horizon: tuple[HorizonBlock, ...],
        urgency,
    ) -> tuple[ScoredBlock, ...]:
        result: list[ScoredBlock] = []
        for block in horizon:
            cost = compute_block_load_cost(
                block,
                load_power_w=load.nominal_power_w,
                allow_battery=self._allow_battery,
                min_battery_soc_pct=self._min_battery_soc_pct,
                fallback_price_sek_kwh=self._fallback_price_sek_kwh,
            )
            result.append(
                score_block(
                    block,
                    load,
                    urgency=urgency,
                    load_cost=cost,
                    allow_battery=self._allow_battery,
                    min_battery_soc_pct=self._min_battery_soc_pct,
                    weights=DEFAULT_WEIGHTS,
                )
            )
        return tuple(result)

    def _filter_eligible_blocks(
        self,
        scored: tuple[ScoredBlock, ...],
        load: FlexibleLoad,
        now: datetime,
    ) -> tuple[ScoredBlock, ...]:
        min_blocks = max(1, int(load.minimum_runtime.total_seconds() / (15 * 60)))
        return tuple(
            s
            for s in scored
            if load.earliest_start <= s.block.timestamp < load.latest_finish
            and s.block.timestamp >= now - timedelta(minutes=15)
            and s.load_feasible
        ) or scored

    def _best_window(
        self,
        load: FlexibleLoad,
        scored: tuple[ScoredBlock, ...],
        strategy: LoadStrategy,
        urgency,
        now: datetime,
    ) -> PlanWindow | None:
        if not scored:
            return None

        interval_minutes = 15
        min_blocks = max(1, int(load.minimum_runtime.total_seconds() / (interval_minutes * 60)))
        max_blocks = max(min_blocks, int(load.maximum_runtime.total_seconds() / (interval_minutes * 60)))

        candidates: list[PlanWindow] = []
        for start_idx in range(len(scored)):
            for length in range(min_blocks, min(max_blocks, len(scored) - start_idx) + 1):
                window_blocks = scored[start_idx : start_idx + length]
                if not window_blocks:
                    continue
                if strategy == LoadStrategy.SOLAR_ONLY:
                    avg_surplus = sum(b.block.available_surplus_w for b in window_blocks) / len(window_blocks)
                    if avg_surplus < load.nominal_power_w * 0.5:
                        continue
                if strategy == LoadStrategy.CHEAPEST:
                    avg_cost = sum(b.marginal_cost_sek_kwh for b in window_blocks) / len(window_blocks)
                    score = -avg_cost
                else:
                    score = sum(b.score for b in window_blocks) / len(window_blocks)

                start = window_blocks[0].block.timestamp
                end = window_blocks[-1].block.timestamp + timedelta(minutes=interval_minutes)
                energy_kwh = (load.nominal_power_w / 1000.0) * (length * interval_minutes / 60.0)
                cost = sum(
                    b.marginal_cost_sek_kwh * (load.nominal_power_w / 1000.0) * (interval_minutes / 60.0)
                    for b in window_blocks
                ) / max(len(window_blocks), 1) * length

                sources = [b.expected_energy_source for b in window_blocks]
                primary = max(set(sources), key=sources.count)

                candidates.append(
                    PlanWindow(
                        start=start,
                        end=end,
                        duration=end - start,
                        expected_energy_kwh=energy_kwh,
                        expected_cost_sek=cost,
                        expected_energy_source=primary,
                        average_score=score,
                        blocks=tuple(window_blocks),
                    )
                )

        if not candidates:
            return None

        if strategy == LoadStrategy.CHEAPEST:
            return min(candidates, key=lambda w: w.expected_cost_sek)
        if strategy == LoadStrategy.SOLAR_ONLY and self._prefer_solar:
            solar_candidates = [c for c in candidates if c.expected_energy_source == EnergySource.SOLAR]
            if solar_candidates:
                return max(solar_candidates, key=lambda w: w.average_score)
        return max(candidates, key=lambda w: w.average_score)

    def _plan_fixed_filter_cycles(
        self,
        load: FlexibleLoad,
        scored: tuple[ScoredBlock, ...],
        eligible: tuple[ScoredBlock, ...],
        strategy: LoadStrategy,
        urgency,
        now: datetime,
        fallback_from_solar: bool,
    ) -> LoadPlan:
        assert load.fixed_cycles_per_day is not None
        assert load.fixed_cycle_duration is not None
        min_separation = load.minimum_cycle_separation or load.minimum_pause or timedelta(minutes=60)

        effective_strategy = strategy
        if strategy == LoadStrategy.SOLAR_ONLY and urgency.tier in {"critical", "urgent"}:
            effective_strategy = LoadStrategy.SMART
            fallback_from_solar = True

        duration_minutes = int(load.fixed_cycle_duration.total_seconds() // 60)
        windows = plan_fixed_filter_cycles(
            scored,
            cycles_per_day=load.fixed_cycles_per_day,
            duration_minutes=duration_minutes,
            min_separation=min_separation,
            earliest=load.earliest_start,
            latest=min(load.latest_finish, load.deadline),
            now=now,
            strategy=effective_strategy,
            nominal_power_w=load.nominal_power_w,
        )

        if not windows and load.safety_critical:
            single = self._fallback_window(load, scored, now)
            windows = (single,) if single else ()

        reason, reason_sv = self._resolve_reason(windows[0] if windows else None, effective_strategy, fallback_from_solar, urgency)
        explanation = self._explain_fixed_filter_windows(
            windows,
            load,
            effective_strategy,
            fallback_from_solar,
        )

        baseline = self._baseline_cost(load, scored)
        planned = sum(w.expected_cost_sek for w in windows) if windows else None
        savings = (baseline - planned) if baseline is not None and planned is not None else None

        return self._build_plan(
            load,
            strategy=strategy,
            windows=windows,
            scored=scored,
            reason=reason if windows else "no_window",
            reason_sv=reason_sv if windows else "ingen_plan",
            explanation_sv=explanation,
            fallback_from_solar=fallback_from_solar,
            baseline_cost_sek=baseline,
            planned_cost_sek=planned,
            savings_sek=savings,
        )

    def _explain_fixed_filter_windows(
        self,
        windows: tuple[PlanWindow, ...],
        load: FlexibleLoad,
        strategy: LoadStrategy,
        fallback_from_solar: bool,
    ) -> str:
        if not windows:
            return "Ingen filterplan kunde skapas inom dagens tidsfönster."
        total_h = sum(w.duration.total_seconds() for w in windows) / 3600.0
        cycle_h = (load.fixed_cycle_duration.total_seconds() / 3600.0) if load.fixed_cycle_duration else 0
        parts = [
            f"EMIC har planerat {len(windows)} filtercykler à {cycle_h:g} h "
            f"({total_h:g} h totalt)."
        ]
        if fallback_from_solar:
            parts.append("Sol-only kunde inte uppfyllas — smart fallback används.")
        elif strategy == LoadStrategy.SOLAR_ONLY:
            parts.append("Prioriterar solel inom varje 2-timmarscykel.")
        return " ".join(parts)

    def _plan_daily_cleaning(
        self,
        load: FlexibleLoad,
        scored: tuple[ScoredBlock, ...],
        eligible: tuple[ScoredBlock, ...],
        strategy: LoadStrategy,
        urgency,
        now: datetime,
        fallback_from_solar: bool,
    ) -> LoadPlan:
        assert load.daily_runtime_target is not None
        assert load.max_starts_per_day is not None
        min_pause = load.minimum_pause or timedelta(minutes=20)

        effective_strategy = strategy
        if strategy == LoadStrategy.SOLAR_ONLY and urgency.tier in {"critical", "urgent"}:
            effective_strategy = LoadStrategy.SMART
            fallback_from_solar = True

        windows = plan_daily_cleaning_windows(
            scored,
            daily_hours=load.daily_runtime_target.total_seconds() / 3600.0,
            min_cycle=load.minimum_runtime,
            min_pause=min_pause,
            max_starts=load.max_starts_per_day,
            earliest=load.earliest_start,
            latest=min(load.latest_finish, load.deadline),
            now=now,
            strategy=effective_strategy,
            nominal_power_w=load.nominal_power_w,
        )

        if not windows and load.safety_critical:
            single = self._fallback_window(load, scored, now)
            windows = (single,) if single else ()

        reason, reason_sv = self._resolve_reason(windows[0] if windows else None, effective_strategy, fallback_from_solar, urgency)
        explanation = self._explain_daily_windows(windows, load, effective_strategy, fallback_from_solar)

        baseline = self._baseline_cost(load, scored)
        planned = sum(w.expected_cost_sek for w in windows) if windows else None
        savings = (baseline - planned) if baseline is not None and planned is not None else None

        return self._build_plan(
            load,
            strategy=strategy,
            windows=windows,
            scored=scored,
            reason=reason if windows else "no_window",
            reason_sv=reason_sv if windows else "ingen_plan",
            explanation_sv=explanation,
            fallback_from_solar=fallback_from_solar,
            baseline_cost_sek=baseline,
            planned_cost_sek=planned,
            savings_sek=savings,
        )

    def _explain_daily_windows(
        self,
        windows: tuple[PlanWindow, ...],
        load: FlexibleLoad,
        strategy: LoadStrategy,
        fallback: bool,
    ) -> str:
        if not windows:
            return "EMIC kunde inte hitta lämpliga cleaning-fönster inom tillåten tid."
        daily_hours = load.daily_runtime_target.total_seconds() / 3600.0 if load.daily_runtime_target else 0
        parts = [f"{w.start.strftime('%H:%M')}–{w.end.strftime('%H:%M')}" for w in windows]
        schedule = ", ".join(parts)
        if fallback:
            return (
                f"EMIC planerar {daily_hours:g} h cleaning fördelat på {len(windows)} period(er): {schedule}. "
                "Solel räckte inte till alla perioder — kompletterar med smart schemaläggning."
            )
        return (
            f"EMIC planerar {daily_hours:g} h cleaning fördelat på {len(windows)} period(er): {schedule}. "
            "Färre starter prioriteras framför korta spridda körningar."
        )

    def _fallback_window(
        self,
        load: FlexibleLoad,
        scored: tuple[ScoredBlock, ...],
        now: datetime,
    ) -> PlanWindow | None:
        """Safety-critical fallback: pick earliest feasible window before deadline."""
        interval_minutes = 15
        min_blocks = max(1, int(load.minimum_runtime.total_seconds() / (interval_minutes * 60)))
        eligible = [s for s in scored if s.block.timestamp >= now and s.block.timestamp < load.deadline]
        if len(eligible) < min_blocks:
            eligible = list(scored[-min_blocks:]) if scored else []
        if not eligible:
            return None
        window_blocks = eligible[:min_blocks]
        start = window_blocks[0].block.timestamp
        end = start + load.minimum_runtime
        energy_kwh = (load.nominal_power_w / 1000.0) * (min_blocks * interval_minutes / 60.0)
        cost = sum(b.marginal_cost_sek_kwh for b in window_blocks) / len(window_blocks) * energy_kwh
        return PlanWindow(
            start=start,
            end=end,
            duration=end - start,
            expected_energy_kwh=energy_kwh,
            expected_cost_sek=cost,
            expected_energy_source=EnergySource.GRID,
            average_score=0.0,
            blocks=tuple(window_blocks),
        )

    def _window_from_fixed(
        self,
        load: FlexibleLoad,
        scored: tuple[ScoredBlock, ...],
        eligible: tuple[ScoredBlock, ...],
    ) -> PlanWindow | None:
        assert load.fixed_start is not None and load.fixed_end is not None
        blocks = tuple(s for s in scored if load.fixed_start <= s.block.timestamp < load.fixed_end)
        if not blocks:
            blocks = eligible[: max(1, int(load.minimum_runtime.total_seconds() / 900))]
        if not blocks:
            return None
        energy_kwh = (load.nominal_power_w / 1000.0) * (load.fixed_end - load.fixed_start).total_seconds() / 3600.0
        cost = sum(b.marginal_cost_sek_kwh for b in blocks) / len(blocks) * energy_kwh
        return PlanWindow(
            start=load.fixed_start,
            end=load.fixed_end,
            duration=load.fixed_end - load.fixed_start,
            expected_energy_kwh=energy_kwh,
            expected_cost_sek=cost,
            expected_energy_source=blocks[0].expected_energy_source,
            average_score=sum(b.score for b in blocks) / len(blocks),
            blocks=blocks,
        )

    def _baseline_cost(self, load: FlexibleLoad, scored: tuple[ScoredBlock, ...]) -> float | None:
        if not scored:
            return None
        hours = load.minimum_runtime.total_seconds() / 3600.0
        energy_kwh = (load.nominal_power_w / 1000.0) * hours
        avg_cost = sum(s.marginal_cost_sek_kwh for s in scored) / len(scored)
        return energy_kwh * avg_cost

    def _resolve_reason(
        self,
        window: PlanWindow | None,
        strategy: LoadStrategy,
        fallback: bool,
        urgency,
    ) -> tuple[str, str]:
        if window is None:
            return "no_window", "ingen_plan"
        if fallback:
            return "solar_only_fallback_safety", "solel_fallback_sakerhet"
        if urgency.run_regardless:
            return "deadline_critical", "deadline_kritisk"
        if window.expected_energy_source == EnergySource.SOLAR:
            return "solar_surplus", "sol_overskott"
        if strategy == LoadStrategy.CHEAPEST:
            return "cheapest_energy", "billigaste_energi"
        return "smart_scheduled", "smart_planerad"

    def _explain_window(
        self,
        window: PlanWindow | None,
        strategy: LoadStrategy,
        fallback: bool,
    ) -> str:
        if window is None:
            return "EMIC kunde inte hitta ett lämpligt fönster inom tillåten tid."
        start_local = window.start.strftime("%H:%M")
        end_local = window.end.strftime("%H:%M")
        if fallback:
            return (
                f"Cleaning kunde inte genomföras enbart med solel och planeras nu {start_local}–{end_local} "
                "för att uppfylla spaets säkerhetskrav."
            )
        if window.expected_energy_source == EnergySource.SOLAR:
            return (
                f"EMIC har valt {start_local}–{end_local} eftersom solöverskottet förväntas vara "
                f"tillräckligt under denna period. Beräknad nätimport: "
                f"{max(0.0, window.expected_energy_kwh * 0.1):.1f} kWh."
            )
        if strategy == LoadStrategy.CHEAPEST:
            return f"EMIC har valt {start_local}–{end_local} baserat på de billigaste timmarna inom fönstret."
        return f"EMIC har valt {start_local}–{end_local} som bästa kompromiss mellan pris, solel och deadline."

    def _explain_fixed(self, fixed: PlanWindow | None, alt: PlanWindow | None) -> str:
        if fixed is None:
            return "Fast schema är konfigurerat men kunde inte analyseras."
        msg = f"Fast schema: {fixed.start.strftime('%H:%M')}–{fixed.end.strftime('%H:%M')}. EMIC flyttar inte schemat."
        if alt and alt.expected_cost_sek < fixed.expected_cost_sek:
            saving = fixed.expected_cost_sek - alt.expected_cost_sek
            msg += f" Bättre tid finns: {alt.start.strftime('%H:%M')}–{alt.end.strftime('%H:%M')} (ca {saving:.2f} kr billigare)."
        return msg

    def _build_plan(
        self,
        load: FlexibleLoad,
        *,
        strategy: LoadStrategy,
        windows: tuple[PlanWindow, ...],
        scored: tuple[ScoredBlock, ...],
        reason: str,
        reason_sv: str,
        explanation_sv: str,
        fallback_from_solar: bool,
        fixed_schedule_analysis: bool = False,
        alternative_windows: tuple[PlanWindow, ...] = (),
        baseline_cost_sek: float | None = None,
        planned_cost_sek: float | None = None,
        savings_sek: float | None = None,
    ) -> LoadPlan:
        return LoadPlan(
            load_id=load.load_id,
            strategy=strategy,
            windows=windows,
            reason=reason,
            reason_sv=reason_sv,
            explanation_sv=explanation_sv,
            fallback_from_solar_only=fallback_from_solar,
            fixed_schedule_analysis=fixed_schedule_analysis,
            alternative_windows=alternative_windows,
            scored_blocks=scored,
            baseline_cost_sek=baseline_cost_sek,
            planned_cost_sek=planned_cost_sek,
            savings_sek=savings_sek,
        )
