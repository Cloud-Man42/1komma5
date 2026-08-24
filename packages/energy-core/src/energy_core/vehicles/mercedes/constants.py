"""Mercedes me integration constants (from mbapi2020 upstream, MIT)."""

from __future__ import annotations

REGION_EUROPE = "Europe"
REGION_NORAM = "North America"
REGION_APAC = "Asia-Pacific"
REGION_CHINA = "China"

DEFAULT_LOCALE = "en-GB"
DEFAULT_COUNTRY_CODE = "EN"

LOGIN_APP_ID_EU = "62778dc4-1de3-44f4-af95-115f06a3a008"
LOGIN_APP_ID_CN = "3f36efb1-f84b-4402-b5a2-68a118fec33e"
LOGIN_BASE_URI = "https://id.mercedes-benz.com"
LOGIN_BASE_URI_CN = "https://ciam-1.mercedes-benz.com.cn"

REST_API_BASE = "https://bff.emea-prod.mobilesdk.mercedes-benz.com"
REST_API_BASE_CN = "https://bff.cn-prod.mobilesdk.mercedes-benz.com"
REST_API_BASE_NA = "https://bff.amap-prod.mobilesdk.mercedes-benz.com"
REST_API_BASE_PA = "https://bff.amap-prod.mobilesdk.mercedes-benz.com"

WEBSOCKET_API_BASE = "wss://websocket.emea-prod.mobilesdk.mercedes-benz.com/v2/ws"
WEBSOCKET_API_BASE_NA = "wss://websocket.amap-prod.mobilesdk.mercedes-benz.com/v2/ws"
WEBSOCKET_API_BASE_PA = "wss://websocket.amap-prod.mobilesdk.mercedes-benz.com/v2/ws"
WEBSOCKET_API_BASE_CN = "wss://websocket.cn-prod.mobilesdk.mercedes-benz.com/v2/ws"

WIDGET_API_BASE = "https://widget.emea-prod.mobilesdk.mercedes-benz.com"
WIDGET_API_BASE_NA = "https://widget.amap-prod.mobilesdk.mercedes-benz.com"
WIDGET_API_BASE_PA = "https://widget.amap-prod.mobilesdk.mercedes-benz.com"
WIDGET_API_BASE_CN = "https://widget.cn-prod.mobilesdk.mercedes-benz.com"

RIS_APPLICATION_VERSION = "1.68.0 (3060)"
RIS_SDK_VERSION = "4.10.0"
RIS_OS_VERSION = "26.3"
RIS_OS_NAME = "ios"
WEBSOCKET_USER_AGENT = "Mercedes-Benz/3044 CFNetwork/3860.400.22 Darwin/25.3.0"

OAUTH_CLIENT_ID = LOGIN_APP_ID_EU
OAUTH_REDIRECT_URI = "rismycar://login-callback"
OAUTH_SCOPE = "email profile ciam-uid phone openid offline_access"

TOKEN_REFRESH_SKEW_SECONDS = 60
STALE_TELEMETRY_SECONDS = 300

ATTRIBUTE_SOC = "soc"
ATTRIBUTE_MAX_SOC = "max_soc"
ATTRIBUTE_CHARGING_POWER_KW = "chargingpowerkw"
ATTRIBUTE_RANGE_ELECTRIC_KM = "rangeElectricKm"
ATTRIBUTE_CHARGING_STATUS = "chargingstatus"
ATTRIBUTE_CHARGING_ACTIVE = "chargingactive"


def login_base_url(region: str) -> str:
    if region == REGION_CHINA:
        return LOGIN_BASE_URI_CN
    return LOGIN_BASE_URI


def rest_api_base(region: str) -> str:
    if region == REGION_APAC:
        return REST_API_BASE_PA
    if region == REGION_CHINA:
        return REST_API_BASE_CN
    if region == REGION_NORAM:
        return REST_API_BASE_NA
    return REST_API_BASE


def websocket_url(region: str) -> str:
    if region in (REGION_APAC, REGION_NORAM):
        return WEBSOCKET_API_BASE_NA
    if region == REGION_CHINA:
        return WEBSOCKET_API_BASE_CN
    return WEBSOCKET_API_BASE


def widget_api_base(region: str) -> str:
    if region == REGION_APAC:
        return WIDGET_API_BASE_PA
    if region == REGION_CHINA:
        return WIDGET_API_BASE_CN
    if region == REGION_NORAM:
        return WIDGET_API_BASE_NA
    return WIDGET_API_BASE
