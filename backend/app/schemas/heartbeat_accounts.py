from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class HeartbeatAccountResponse(BaseModel):
    id: int
    slug: str
    name: str
    provider: str
    connection_type: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    auth_domain: str = ""
    auth_realm: str = ""
    auth_client_id: str = ""
    username_masked: str
    password_configured: bool
    api_token_configured: bool
    refresh_token_configured: bool = False
    api_url: str | None = None
    token_expires_at: datetime | None = None
    is_enabled: bool
    status: str
    linked_sites: list[str] = Field(default_factory=list)
    last_authentication_at: datetime | None = None
    last_successful_authentication_at: datetime | None = None
    last_api_call_at: datetime | None = None
    last_successful_api_call_at: datetime | None = None
    last_authentication_error: str | None = None
    updated_at: datetime | None = None


class HeartbeatAccountCreateRequest(BaseModel):
    slug: str
    name: str
    username: str
    password: str
    is_enabled: bool = True

    @field_validator("slug", "name", "username", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str:
        return (value or "").strip()


class HeartbeatAccountUpdateRequest(BaseModel):
    name: str | None = None
    username: str | None = None
    password: str | None = None
    is_enabled: bool | None = None

    @field_validator("name", "username", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class HeartbeatProbeResult(BaseModel):
    path: str
    ok: bool
    status_code: int | None = None
    detail: str = ""


class HeartbeatAccountDiagnosticsResponse(BaseModel):
    account_id: int
    slug: str
    name: str
    provider: str
    status: str
    api_url: str | None = None
    system_id: str | None = None
    gateway_id: str | None = None
    token_ok: bool
    token_expires_at: datetime | None = None
    last_authentication_error: str | None = None
    linked_sites: list[str] = Field(default_factory=list)
    probes: list[HeartbeatProbeResult] = Field(default_factory=list)


class HeartbeatAccountTestConnectionResponse(BaseModel):
    account_id: int
    slug: str
    connected: bool
    provider: str | None = None
    api_url: str | None = None
    probe_path: str | None = None
    visible_installations: int = 0
    last_authentication_error: str | None = None


class HeartbeatInstallationResponse(BaseModel):
    name: str | None = None
    system_id: str | None = None
    site_id: str | None = None
    asset_id: str | None = None
    device_id: str | None = None
    gateway_id: str | None = None
    serial_number: str | None = None


class HeartbeatSerialDiscoveryResponse(BaseModel):
    serial: str
    found: bool
    resolved_site_id: str | None = None
    resolved_system_id: str | None = None
    resolved_asset_id: str | None = None
    resolved_device_id: str | None = None


class HeartbeatDiscoveryResponse(BaseModel):
    account_id: int
    slug: str
    provider: str
    api_url: str | None = None
    authentication_ok: bool
    installations: list[HeartbeatInstallationResponse] = Field(default_factory=list)
    serial_matches: list[HeartbeatSerialDiscoveryResponse] = Field(default_factory=list)
    paths_probed: list[str] = Field(default_factory=list)


class HeartbeatAccountLinkSiteRequest(BaseModel):
    site_slug: str
    heartbeat_serial_number: str | None = None
    heartbeat_system_id: str | None = None
    heartbeat_gateway_id: str | None = None
    heartbeat_site_id: str | None = None
    heartbeat_asset_id: str | None = None
    heartbeat_device_id: str | None = None

    @field_validator("site_slug", mode="before")
    @classmethod
    def strip_slug(cls, value: str | None) -> str:
        slug = (value or "").strip()
        if not slug:
            raise ValueError("site_slug krävs")
        return slug


class HeartbeatAccountLinkSiteResponse(BaseModel):
    site_slug: str
    heartbeat_account_id: int
    heartbeat_system_id: str | None = None
    heartbeat_gateway_id: str | None = None
    heartbeat_serial_number: str | None = None
    heartbeat_site_id: str | None = None
    heartbeat_asset_id: str | None = None
    heartbeat_device_id: str | None = None


class HeartbeatGlobalDiagnosticsAccount(BaseModel):
    slug: str
    name: str
    configured: bool
    authentication: str
    status: str
    api_url: str | None = None
    provider: str
    linked_sites: list[str] = Field(default_factory=list)
    visible_installations: int = 0
    serial_number: str | None = None
    serial_match: str | None = None
    system_id: str | None = None
    gateway_id: str | None = None
    site_id: str | None = None
    asset_id: str | None = None
    device_id: str | None = None


class HeartbeatGlobalDiagnosticsComparison(BaseModel):
    same_api_server: str
    same_auth_mechanism: str
    same_response_schema: str
    separate_account_context: str
    same_tenant: str


class HeartbeatGlobalDiagnosticsResponse(BaseModel):
    accounts: list[HeartbeatGlobalDiagnosticsAccount]
    comparison: HeartbeatGlobalDiagnosticsComparison
