"""Benchmark solar forecast route from inside the backend container."""

from __future__ import annotations

import statistics
import time
import urllib.request


def main() -> None:
    url = "http://127.0.0.1:8000/api/sites/akarp/solar/forecast"
    samples: list[float] = []
    for _ in range(3):
        urllib.request.urlopen(url, timeout=120).read()
    for _ in range(10):
        start = time.perf_counter()
        urllib.request.urlopen(url, timeout=120).read()
        samples.append((time.perf_counter() - start) * 1000)
    samples.sort()
    p95_index = max(0, int(len(samples) * 0.95) - 1)
    print(f"p95_ms={samples[p95_index]:.1f}")
    print(f"avg_ms={statistics.mean(samples):.1f}")


if __name__ == "__main__":
    main()
