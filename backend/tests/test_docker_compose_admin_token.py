"""Ensure production services receive EMIC_ADMIN_TOKEN from docker-compose."""

from pathlib import Path


def test_collector_service_requires_emic_admin_token_in_compose() -> None:
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(encoding="utf-8")
    collector_block = compose.split("collector:", 1)[1].split("\n  postgres:", 1)[0]
    assert "EMIC_ADMIN_TOKEN: ${EMIC_ADMIN_TOKEN:?EMIC_ADMIN_TOKEN is required}" in collector_block
