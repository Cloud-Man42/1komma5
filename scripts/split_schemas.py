"""One-off helper: split backend/app/schemas.py into app/schemas/*.py."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "backend" / "app" / "schemas.py"
OUT = REPO / "backend" / "app" / "schemas"

HEADER = """from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

"""


def domain_for(class_name: str) -> str:
    rules = [
        ("sites", ("ReadingResponse", "SiteResponse", "SiteCreate", "SiteUpdate", "SiteEnergyConfig")),
        ("ev", ("EvCharger", "EvBridge", "EnergyBalance", "VirtualEvse", "EnergyReasoning", "SolarChargingPlan", "EvCharging", "EvEnergySources")),
        ("readings", ("AggregatedReading", "HistoryResponse", "PeakReading", "PeaksResponse", "FinancialStat", "FinancialStats", "ForecastValues", "MonthlyForecast", "YearForecast", "HistoricalEnergy", "MarketPrice")),
        ("heartbeat", ("SiteHeartbeat", "HeartbeatConfig", "ChargeAmpsConfig", "Timescale", "ChargerReadiness", "ChargingReadiness")),
        ("solar", ("SolarSite", "SolarForecast", "SolarAccuracy", "SolarDiagnostics", "SolarEnergyBudget", "SolarHourly", "SolarPerformance", "SolarRadiation", "DmiForecast", "SolarModel", "SolarProvider", "SolarIntelligence", "SolarWeather")),
        ("spa", ("Spa",)),
        ("chargers_catalog", ("ChargerManufacturer", "ChargerCatalog", "ChargerIntegration", "ChargerModel", "ChargerConnection")),
        ("dashboard", ("Dashboard",)),
        ("vehicles", ("Vehicle", "StationCandidate")),
        ("chargefinder", ("ChargeFinder",)),
        ("heartbeat_bridge", ("HeartbeatDiscovery", "HeartbeatBridge", "HeartbeatEvMapping", "HeartbeatWrite", "HeartbeatReplay")),
        ("orchestration", ("EnergyOrchestration",)),
        ("pricing", ("PricePeriod", "PriceEngine", "EvRecommendation", "EnergyStrategy")),
        ("intelligence_advisor", ("BatteryOpportunity", "HorizonLoad", "HorizonOptimizer")),
        ("heartbeat_audit", ("HeartbeatAudit",)),
        ("forecast_learning", ("ForecastMetric", "ForecastSnapshot", "ForecastLearning")),
        ("energy_control", ("EnergyControl", "AdminAudit")),
    ]
    for domain, prefixes in rules:
        if any(class_name.startswith(prefix) for prefix in prefixes):
            return domain
    return "misc"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    # skip module header through first class
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
    for domain, chunks in sorted(by_domain.items()):
        (OUT / f"{domain}.py").write_text(HEADER + "\n\n\n".join(chunks) + "\n", encoding="utf-8")

    init = [
        '"""API schemas split by domain."""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for domain in sorted(by_domain):
        init.append(f"from app.schemas.{domain} import *  # noqa: F403")
    init.append("")
    (OUT / "__init__.py").write_text("\n".join(init) + "\n", encoding="utf-8")

    # compatibility shim at former module path
    shim = [
        '"""Compatibility shim — import from app.schemas package."""',
        "",
        "from app.schemas import *  # noqa: F403",
        "",
    ]
    SRC.write_text("\n".join(shim) + "\n", encoding="utf-8")
    print(f"Split {len(blocks)} classes into {len(by_domain)} domain modules")


if __name__ == "__main__":
    main()
