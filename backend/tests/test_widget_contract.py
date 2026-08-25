"""Contract tests: backend widget JSON must match committed Apple fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import seed_recent_readings

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "apple" / "Fixtures"


async def _create_device(ac) -> str:
    response = await ac.post(
        "/api/apple-devices",
        json={
            "owner_label": "Contract",
            "device_name": "Fixture Device",
            "device_type": "iphone",
            "default_site_slug": "akarp",
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def _normalize(payload: dict) -> dict:
    payload = dict(payload)
    payload.pop("updatedAt", None)
    payload.pop("dataAgeSeconds", None)
    if "sites" in payload:
        for site in payload["sites"]:
            site.pop("updatedAt", None)
            site.pop("dataAgeSeconds", None)
    return payload


@pytest.mark.asyncio
async def test_widget_status_matches_fixture(client):
    ac, session_factory, settings = client
    token = await _create_device(ac)
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(5420, 1610, 0, 1470, 74)],
    )
    response = await ac.get(
        "/api/v1/widget/status/akarp",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = _normalize(response.json())
    fixture_path = FIXTURES_DIR / "widget-status-akarp.json"
    if not fixture_path.exists():
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert body["site"] == expected["site"]
    assert body["battery"]["state"] == expected["battery"]["state"]
    assert body["grid"]["direction"] == expected["grid"]["direction"]
    assert body["emic"]["decisionText"] == expected["emic"]["decisionText"]
