"""One-off helper: split energy_core/db/models.py into db/models/*.py."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages" / "energy-core" / "src" / "energy_core" / "db" / "models.py"
OUT = REPO / "packages" / "energy-core" / "src" / "energy_core" / "db" / "models"

HEADER = """from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base

"""

BASE_HEADER = """from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
"""


def domain_for(class_name: str) -> str:
    if class_name == "Base":
        return "base"
    rules: list[tuple[str, tuple[str, ...]]] = [
        ("sites", ("SiteModel", "SiteEnergyConfigModel", "SiteLiveSnapshotModel")),
        ("ev", ("EvCharger", "EvCharging", "EvBridge", "VirtualCharger")),
        ("readings", ("EnergyReadingModel", "EnergyHourlyModel", "EnergyDailyModel")),
        ("pricing", ("MarketPrice", "PricePeriod", "PriceEngineState", "FinancialDaily")),
        (
            "energy_control",
            ("EnergyControlAction", "EnergyForecastSnapshot", "AdminAuditLog", "FlexibleLoadPlan"),
        ),
        ("balance", ("BatteryEnergyLedger", "HistoricalMonthlyEnergy", "EnergyBalanceSnapshot")),
        ("solar", ("Solar",)),
        ("heartbeat", ("Heartbeat",)),
        ("consumer", ("EnergyConsumer", "ConsumerSample", "ConsumerInterval", "ConsumerAggregate")),
        ("spa", ("Spa",)),
        ("vehicles", ("Vehicle",)),
        (
            "charging_stations",
            ("ChargingLocation", "ChargingStation", "ChargeFinderIntegration"),
        ),
        ("system", ("AppleDevice", "CollectorTaskRun", "IntegrationHealth")),
    ]
    for domain, prefixes in rules:
        if any(class_name.startswith(prefix) for prefix in prefixes):
            return domain
    raise ValueError(f"No domain mapping for {class_name}")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("class "))
    lines = lines[start:]

    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("class ") and current:
            blocks.append("\n".join(current).rstrip())
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).rstrip())

    by_domain: dict[str, list[str]] = {}
    for block in blocks:
        class_name = block.split("(")[0].split()[-1]
        domain = domain_for(class_name)
        by_domain.setdefault(domain, []).append(block)

    OUT.mkdir(exist_ok=True)
    (OUT / "base.py").write_text(BASE_HEADER + "\n", encoding="utf-8")

    for domain, chunks in sorted(by_domain.items()):
        if domain == "base":
            continue
        (OUT / f"{domain}.py").write_text(HEADER + "\n\n\n".join(chunks) + "\n", encoding="utf-8")

    init = [
        '"""ORM models split by domain. Import all modules so Base.metadata is complete."""',
        "",
        "from __future__ import annotations",
        "",
        "from energy_core.db.models.base import Base",
        "",
    ]
    for domain in sorted(by_domain):
        if domain == "base":
            continue
        init.append(f"from energy_core.db.models.{domain} import *  # noqa: F403")
    init.append("")
    init.append("__all__ = [name for name in dir() if not name.startswith('_')]")
    init.append("")
    (OUT / "__init__.py").write_text("\n".join(init) + "\n", encoding="utf-8")

    SRC.unlink()
    print(f"Split {len(blocks)} classes into {len(by_domain)} domain modules")


if __name__ == "__main__":
    main()
