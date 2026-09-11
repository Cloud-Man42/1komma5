"""Sensibo module unit tests (Sprint E)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parents[2] / "modules" / "sensibo" / "module"
sys.path.insert(0, str(MODULE_DIR))

from adapter import normalize_pod_reading  # noqa: E402
from sensibo_client import SensiboClient, SensiboClientError  # noqa: E402


def test_list_pods_success():
    def request_fn(**kwargs):
        assert kwargs["method"] == "GET"
        return {"status_code": 200, "body": json.dumps({"result": [{"id": "abc", "room": "Living"}]})}

    client = SensiboClient(api_key="key", request_fn=request_fn)
    pods = client.list_pods()
    assert len(pods) == 1


def test_auth_failure_no_retry():
    calls = {"n": 0}

    def request_fn(**kwargs):
        calls["n"] += 1
        return {"status_code": 401, "body": ""}

    client = SensiboClient(api_key="bad", request_fn=request_fn, max_retries=2)
    with pytest.raises(SensiboClientError):
        client.list_pods()
    assert calls["n"] == 1


def test_normalize_full_payload():
    reading = normalize_pod_reading(
        pod={"id": "pod1", "room": "Office", "connectionStatus": "Connected", "acState": {"mode": "cool", "targetTemperature": 22.0}},
        measurement={"temperature": 21.5, "humidity": 45.0, "time": "2026-09-09T10:00:00+00:00"},
        site_id=1,
    )
    assert reading["temperature_c"] == 21.5
    assert reading["online"] is True


def test_sensibo_client_read_only_methods():
    source = (MODULE_DIR / "sensibo_client.py").read_text(encoding="utf-8")
    for verb in ("POST", "PUT", "PATCH", "DELETE"):
        assert f'method="{verb}"' not in source
        assert f"'{verb}'" not in source or verb == "GET"
    assert "ALLOWED_METHODS" in source


def test_sensibo_module_no_core_imports():
    root = Path(__file__).resolve().parents[2] / "modules" / "sensibo"
    forbidden = ("energy_core", "backend", "sqlalchemy", "fastapi")
    for path in root.rglob("*.py"):
        if path.name in {"build_emicpkg.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} imports forbidden {token}"


def test_build_module_accepts_health_gate_context():
    from types import SimpleNamespace

    sys.path.insert(0, str(MODULE_DIR))
    import module as sensibo_module  # noqa: E402

    ctx = SimpleNamespace(
        module_id="integration.sensibo",
        site_id="1",
        installed_version="1.0.0",
        configuration={},
    )
    runtime = sensibo_module.build_module(ctx)
    status = runtime.health()
    assert status.level == "ok"
