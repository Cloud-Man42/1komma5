"""Public HeartBeat connection metadata derived from stored settings."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRecord, SiteHeartbeatMapping
from energy_core.heartbeat_connection import HeartbeatConnectionType, connection_type_label


@dataclass(frozen=True)
class HeartbeatConnectionInfo:
    connection_type: str
    connection_type_label: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    poll_interval_seconds: int
    dashboard_refresh_seconds: int
    api_url: str | None
    username: str
    password_configured: bool
    api_token_configured: bool
    connection_mode: str
    contacting_component: str
    implementation_status: str
    notes: tuple[str, ...]
    sites: tuple[SiteHeartbeatMapping, ...]


def build_heartbeat_connection_info(
    settings: HeartbeatSettingsRecord,
    sites: list[SiteHeartbeatMapping],
) -> HeartbeatConnectionInfo:
    connection_type = HeartbeatConnectionType(settings.connection_type)

    if connection_type == HeartbeatConnectionType.MOCK:
        status = "mock"
        notes = (
            "Collector använder syntetisk testdata utan nätverksanrop.",
            "Byt anslutningstyp till molntjänst eller lokal gateway när du vill ansluta mot HeartBeat.",
        )
    elif connection_type == HeartbeatConnectionType.CLOUD:
        if not settings.username and not settings.api_token_configured:
            status = "not_configured"
            notes = (
                "Molntjänsten nås via https://heartbeat.1komma5grad.com (port 443).",
                "Ange 1Komma5-konto (e-post/lösenord) eller Bearer-token.",
                "Varje anläggning behöver ett system-ID (UUID) från HeartBeat.",
                "ChargeAmp Halo i 1Komma5-system styrs via HeartBeat EV-API (SMART/SOLAR/QUICK).",
            )
        else:
            status = "configured"
            notes = (
                "Collector anropar 1Komma5 HeartBeat API i molnet (HTTPS, port 443).",
                "Live-data hämtas via /api/v3/systems/{uuid}/live-overview.",
                "Laddboxar (t.ex. ChargeAmp Halo) styrs via /devices/evs när de är kopplade i HeartBeat.",
                "Bearer-token förnyas automatiskt från sparat lösenord (~24h JWT).",
            )
    elif connection_type == HeartbeatConnectionType.LOCAL:
        if not settings.host:
            status = "not_configured"
            notes = (
                "Ange IP eller värdnamn till lokal HeartBeat-gateway.",
                "Port beror på gateway — vanliga värden är 80, 443 eller 8080.",
            )
        else:
            status = "configured"
            notes = (
                f"Collector anropar gateway på {settings.api_url or 'konfigurerad URL'}.",
                "Kontrollera att servern kan nå gateway-IP:t i nätverket.",
            )
    else:
        status = "unknown"
        notes = (f"Okänd anslutningstyp: {settings.connection_type}",)

    if connection_type != HeartbeatConnectionType.MOCK and not any(
        site.external_system_id for site in sites
    ):
        notes = (*notes, "Inga system-ID (UUID) är kopplade till anläggningarna ännu.")

    return HeartbeatConnectionInfo(
        connection_type=settings.connection_type,
        connection_type_label=connection_type_label(settings.connection_type),
        host=settings.host,
        port=settings.port,
        use_tls=settings.use_tls,
        api_path=settings.api_path,
        poll_interval_seconds=settings.poll_interval_seconds,
        dashboard_refresh_seconds=settings.dashboard_refresh_seconds,
        api_url=settings.api_url,
        username=settings.username,
        password_configured=settings.password_configured,
        api_token_configured=settings.api_token_configured,
        connection_mode="outbound_polling",
        contacting_component="collector",
        implementation_status=status,
        notes=notes,
        sites=tuple(sites),
    )
