"""Mercedes mobile SDK app-version headers."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from energy_core.vehicles.mercedes.constants import (
    DEFAULT_LOCALE,
    REGION_APAC,
    RIS_APPLICATION_VERSION,
    RIS_OS_NAME,
    RIS_OS_VERSION,
    RIS_SDK_VERSION,
    WEBSOCKET_USER_AGENT,
)

logger = logging.getLogger(__name__)

APP_VERSION_CHECK_INTERVAL_SECONDS = 21600
UPDATE_REQUIRED_STATUSES = {"FORCE", "INFORM_ALWAYS"}


class MercedesAppVersionManager:
    """Resolve mobile SDK headers; refresh app version from Mercedes /v1/config."""

    def __init__(self, region: str = "Europe") -> None:
        self._region = region
        self._application_name = "mycar-store-ap" if region == REGION_APAC else "mycar-store-ece"
        self._application_version = RIS_APPLICATION_VERSION
        self._last_check_monotonic = 0.0

    @property
    def application_version(self) -> str:
        return self._application_version

    def apply_config(self, config: dict[str, Any]) -> bool:
        """Update cached app version from Mercedes BFF /v1/config payload."""
        updated = False
        force_update = config.get("forceUpdate")
        if isinstance(force_update, dict):
            status = force_update.get("status")
            candidate = _coalesce_version(
                force_update.get("applicationVersion"),
                force_update.get("version"),
                force_update.get("minimumVersion"),
            )
            if candidate and status in UPDATE_REQUIRED_STATUSES:
                updated = self._set_version(candidate, reason=f"forceUpdate.status={status}")
        if not updated:
            candidate = _coalesce_version(
                config.get("applicationVersion"),
                config.get("minimumApplicationVersion"),
            )
            if candidate:
                updated = self._set_version(candidate, reason="config.applicationVersion")
        self._last_check_monotonic = time.monotonic()
        return updated

    async def refresh(self, config_loader, *, force: bool = False) -> bool:
        """Fetch /v1/config and refresh headers when stale or forced."""
        if not force and (time.monotonic() - self._last_check_monotonic) < APP_VERSION_CHECK_INTERVAL_SECONDS:
            return False
        config = await config_loader()
        if not isinstance(config, dict):
            return False
        return self.apply_config(config)

    def _set_version(self, version: str, *, reason: str) -> bool:
        normalized = str(version).strip()
        if not normalized or normalized == self._application_version:
            return False
        logger.info(
            "Updating Mercedes app version for %s from %s to %s (%s)",
            self._region,
            self._application_version,
            normalized,
            reason,
        )
        self._application_version = normalized
        return True

    def oauth_headers(self) -> dict[str, str]:
        headers = {
            "Ris-Os-Name": RIS_OS_NAME,
            "Ris-Os-Version": RIS_OS_VERSION,
            "Ris-Sdk-Version": RIS_SDK_VERSION,
            "Ris-Application-Version": self._application_version,
            "X-Applicationname": self._application_name,
            "X-Locale": DEFAULT_LOCALE,
            "X-Trackingid": str(uuid.uuid4()),
            "X-Sessionid": str(uuid.uuid4()),
            "User-Agent": WEBSOCKET_USER_AGENT,
            "Content-Type": "application/json",
            "Accept-Language": DEFAULT_LOCALE,
        }
        return headers

    def webapi_headers(self, session_id: str) -> dict[str, str]:
        return {
            **self.oauth_headers(),
            "X-SessionId": session_id,
            "X-TrackingId": str(uuid.uuid4()).upper(),
            "ris-os-name": RIS_OS_NAME,
            "ris-os-version": RIS_OS_VERSION,
            "X-ApplicationName": self._application_name,
            "ris-application-version": self._application_version,
            "ris-sdk-version": RIS_SDK_VERSION,
        }

    def websocket_headers(self, session_id: str, access_token: str) -> dict[str, str]:
        return {
            "Authorization": access_token,
            "APP-SESSION-ID": session_id,
            "OUTPUT-FORMAT": "PROTO",
            "X-SessionId": session_id,
            "X-TrackingId": str(uuid.uuid4()).upper(),
            "X-Locale": "de-DE",
            "ris-os-name": RIS_OS_NAME,
            "ris-os-version": RIS_OS_VERSION,
            "X-ApplicationName": self._application_name,
            "ris-application-version": self._application_version,
            "ris-sdk-version": RIS_SDK_VERSION,
            "User-Agent": WEBSOCKET_USER_AGENT,
        }


def _coalesce_version(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None
