"""In-process ChargeFinder lookup metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChargeFinderMetrics:
    chargefinder_lookup_total: int = 0
    chargefinder_lookup_success: int = 0
    chargefinder_lookup_failure: int = 0
    chargefinder_cache_hit: int = 0
    chargefinder_latency_ms_total: int = 0
    chargefinder_parser_failure: int = 0
    chargefinder_blocked: int = 0
    chargefinder_multiple_candidates: int = 0
    chargefinder_station_resolution_success: int = 0

    def record_lookup(self, *, success: bool, latency_ms: int, blocked: bool = False, parser_failure: bool = False) -> None:
        self.chargefinder_lookup_total += 1
        self.chargefinder_latency_ms_total += max(latency_ms, 0)
        if blocked:
            self.chargefinder_blocked += 1
        if parser_failure:
            self.chargefinder_parser_failure += 1
        if success:
            self.chargefinder_lookup_success += 1
        else:
            self.chargefinder_lookup_failure += 1

    def record_cache(self, *, hit: bool) -> None:
        if hit:
            self.chargefinder_cache_hit += 1

    def record_resolution(self, status: str) -> None:
        if status == "MULTIPLE_CANDIDATES":
            self.chargefinder_multiple_candidates += 1
        elif status in {"OK", "DEGRADED"}:
            self.chargefinder_station_resolution_success += 1

    def snapshot(self) -> dict[str, int | float]:
        avg_latency = (
            self.chargefinder_latency_ms_total / self.chargefinder_lookup_total
            if self.chargefinder_lookup_total
            else 0.0
        )
        cache_total = self.chargefinder_cache_hit
        return {
            "chargefinder_lookup_total": self.chargefinder_lookup_total,
            "chargefinder_lookup_success": self.chargefinder_lookup_success,
            "chargefinder_lookup_failure": self.chargefinder_lookup_failure,
            "chargefinder_cache_hit": self.chargefinder_cache_hit,
            "chargefinder_cache_hit_rate": round(
                (self.chargefinder_cache_hit / cache_total) if cache_total else 0.0,
                3,
            ),
            "chargefinder_latency_ms_avg": round(avg_latency, 1),
            "chargefinder_parser_failure": self.chargefinder_parser_failure,
            "chargefinder_blocked": self.chargefinder_blocked,
            "chargefinder_multiple_candidates": self.chargefinder_multiple_candidates,
            "chargefinder_station_resolution_success": self.chargefinder_station_resolution_success,
        }


_global_metrics = ChargeFinderMetrics()


def get_chargefinder_metrics() -> ChargeFinderMetrics:
    return _global_metrics
