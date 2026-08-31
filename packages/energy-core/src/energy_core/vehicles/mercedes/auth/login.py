"""Mercedes CIAM OAuth2 login flow (ported from mbapi2020, MIT)."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
import urllib.parse
import uuid
from typing import Any

import httpx

from energy_core.vehicles.mercedes.auth.app_version import MercedesAppVersionManager
from energy_core.vehicles.mercedes.auth.errors import (
    MercedesAuthError,
    MercedesLegalTermsError,
    MercedesTwoFactorUnsupported,
)
from energy_core.vehicles.mercedes.auth.pkce import generate_pkce_pair
from energy_core.vehicles.mercedes.constants import (
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPE,
    login_base_url,
    rest_api_base,
)

logger = logging.getLogger(__name__)

GATEWAY_ERROR_CODES = (502, 503, 504)
LOGIN_MAX_ATTEMPTS = 3
LOGIN_RETRY_BACKOFF_SECONDS = 5


class MercedesLoginFlow:
    def __init__(
        self,
        *,
        region: str,
        device_guid: str,
        app_version: MercedesAppVersionManager | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._region = region
        self._device_guid = device_guid
        self._app_version = app_version or MercedesAppVersionManager(region)
        self._timeout = timeout
        self._code_verifier: str | None = None
        self._code_challenge: str | None = None
        self._session_id = str(uuid.uuid4())

    async def login(self, email: str, password: str) -> dict[str, Any]:
        logger.info("Mercedes authentication started")
        cookies = httpx.Cookies()
        cookies.set("CIAM.DEVICE", self._device_guid)
        async with httpx.AsyncClient(timeout=self._timeout, cookies=cookies, follow_redirects=True) as client:
            resume = await self._get_authorization_resume(client)
            await self._send_user_agent_info(client)
            await self._submit_username(client, email)
            rid = secrets.token_urlsafe(24)
            pre_login = await self._submit_password(client, email, password, rid)
            if pre_login.get("passkeyDemoEnabled"):
                pre_login = await self._disable_passkey_demo(client, email, password, rid)
            result = pre_login.get("result", "")
            if result == "GOTO_LOGIN_OTP":
                raise MercedesTwoFactorUnsupported("Two-factor authentication is not supported")
            if result == "GOTO_LOGIN_LEGAL_TEXTS":
                pre_login = await self._submit_legal_consent(
                    client,
                    pre_login.get("homeCountry", ""),
                    pre_login.get("consentCountry", ""),
                )
                result = pre_login.get("result", "")
            if result != "RESUME2OIDCP":
                raise MercedesAuthError(f"Unexpected login result: {result}")
            auth_code = await self._resume_authorization(client, resume, pre_login["token"])
            token_info = await self._exchange_code_for_tokens(client, auth_code)
        token_info = _add_expires_at(token_info)
        logger.info("Mercedes authentication successful")
        return token_info

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Exchange the refresh token for a new access token.

        No app-version refresh here. `/v1/config` needs a Bearer token, which is
        the very thing we are missing, and the cached version is what the initial
        login uses too. `MercedesProvider.connect` refreshes it authoritatively.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            headers = self._app_version.oauth_headers()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["X-Device-Id"] = self._device_guid
            headers["X-Request-Id"] = str(uuid.uuid4())
            url = f"{login_base_url(self._region)}/as/token.oauth2"
            data = f"grant_type=refresh_token&refresh_token={refresh_token}"
            response = await client.post(url, content=data, headers=headers)
            if response.status_code >= 400:
                raise MercedesAuthError(f"Token refresh failed: {response.status_code}")
            token_info = response.json()
            if "refresh_token" not in token_info:
                token_info["refresh_token"] = refresh_token
            logger.info("Mercedes access token refreshed")
            return _add_expires_at(token_info)

    def _ensure_pkce(self) -> None:
        if not self._code_verifier:
            self._code_verifier, self._code_challenge = generate_pkce_pair()

    async def _login_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        step: str,
        **kwargs: Any,
    ) -> httpx.Response:
        for attempt in range(1, LOGIN_MAX_ATTEMPTS + 1):
            response = await client.request(method, url, **kwargs)
            if response.status_code in GATEWAY_ERROR_CODES and attempt < LOGIN_MAX_ATTEMPTS:
                await asyncio.sleep(LOGIN_RETRY_BACKOFF_SECONDS * attempt)
                continue
            if response.status_code >= 400:
                raise MercedesAuthError(f"{step} failed: {response.status_code} - {response.text[:200]}")
            return response
        raise MercedesAuthError(f"{step} failed after {LOGIN_MAX_ATTEMPTS} attempts")

    async def _get_authorization_resume(self, client: httpx.AsyncClient) -> str:
        self._ensure_pkce()
        params = {
            "client_id": OAUTH_CLIENT_ID,
            "code_challenge": self._code_challenge,
            "code_challenge_method": "S256",
            "redirect_uri": OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": OAUTH_SCOPE,
        }
        url = f"{login_base_url(self._region)}/as/authorization.oauth2"
        response = await self._login_request(client, "GET", url, "Authorization request", params=params)
        parsed = urllib.parse.urlparse(str(response.url))
        resume = urllib.parse.parse_qs(parsed.query).get("resume", [None])[0]
        if not resume:
            raise MercedesAuthError("Resume parameter not found in authorization response")
        return resume

    async def _send_user_agent_info(self, client: httpx.AsyncClient) -> None:
        url = f"{login_base_url(self._region)}/ciam/auth/ua"
        headers = _mobile_safari_headers(self._region, include_referer=False)
        await client.post(url, json={"browserName": "Mobile Safari", "browserVersion": "15.6.6", "osName": "iOS"}, headers=headers)

    async def _submit_username(self, client: httpx.AsyncClient, email: str) -> None:
        url = f"{login_base_url(self._region)}/ciam/auth/login/user"
        await self._login_request(
            client,
            "POST",
            url,
            "Username submission",
            json={"username": email},
            headers=_mobile_safari_headers(self._region),
        )

    async def _submit_password(
        self,
        client: httpx.AsyncClient,
        email: str,
        password: str,
        rid: str,
    ) -> dict[str, Any]:
        url = f"{login_base_url(self._region)}/ciam/auth/login/pass"
        response = await self._login_request(
            client,
            "POST",
            url,
            "Password submission",
            json={"username": email, "password": password, "rememberMe": False, "rid": rid},
            headers=_mobile_safari_headers(self._region),
        )
        return response.json()

    async def _disable_passkey_demo(
        self,
        client: httpx.AsyncClient,
        email: str,
        password: str,
        rid: str,
    ) -> dict[str, Any]:
        url = f"{login_base_url(self._region)}/ciam/auth/disablePasskeyDemo"
        response = await self._login_request(
            client,
            "POST",
            url,
            "Passkey prompt skip",
            json={
                "username": email,
                "password": password,
                "rememberMe": False,
                "rid": rid,
                "disablePasskeyDemo": True,
            },
            headers=_mobile_safari_headers(self._region),
        )
        return response.json()

    async def _submit_legal_consent(
        self,
        client: httpx.AsyncClient,
        home_country: str,
        consent_country: str,
    ) -> dict[str, Any]:
        url = f"{login_base_url(self._region)}/ciam/auth/toas/saveLoginConsent"
        response = await client.post(
            url,
            json={"texts": {}, "homeCountry": home_country, "consentCountry": consent_country},
            headers=_mobile_safari_headers(self._region),
        )
        if response.status_code >= 400:
            raise MercedesLegalTermsError("Problem accepting legal terms during login")
        return response.json()

    async def _resume_authorization(
        self,
        client: httpx.AsyncClient,
        resume_url: str,
        token: str,
    ) -> str:
        headers = _mobile_safari_headers(self._region)
        headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["content-type"] = "application/x-www-form-urlencoded"
        base = login_base_url(self._region)
        url = resume_url if resume_url.startswith("http") else f"{base}{resume_url}"
        # Must reuse the login session cookies; a fresh client loses CIAM state.
        response = await client.post(
            url,
            data={"token": token},
            headers=headers,
            follow_redirects=False,
        )
        return _code_from_auth_redirect(response, base)

    async def _exchange_code_for_tokens(self, client: httpx.AsyncClient, code: str) -> dict[str, Any]:
        if not self._code_verifier:
            raise MercedesAuthError("Code verifier not available for token exchange")
        headers = self._app_version.oauth_headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(
            {
                "client_id": OAUTH_CLIENT_ID,
                "code": code,
                "code_verifier": self._code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": OAUTH_REDIRECT_URI,
            }
        )
        url = f"{login_base_url(self._region)}/as/token.oauth2"
        response = await client.post(url, content=data, headers=headers)
        if response.status_code >= 400:
            raise MercedesAuthError(f"Token exchange failed: {response.status_code}")
        return response.json()

    async def preflight_config(self, access_token: str) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            headers = self._app_version.webapi_headers(self._session_id)
            headers["Authorization"] = f"Bearer {access_token}"
            url = f"{rest_api_base(self._region)}/v1/config"
            await client.get(url, headers=headers)


def is_token_expired(token_info: dict[str, Any]) -> bool:
    expires_at = token_info.get("expires_at")
    if expires_at is None:
        return True
    return int(expires_at) - int(time.time()) < 60


def _add_expires_at(token_info: dict[str, Any]) -> dict[str, Any]:
    token_info = dict(token_info)
    token_info["expires_at"] = int(time.time()) + int(token_info.get("expires_in", 0))
    return token_info


REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)


def _code_from_auth_redirect(response: httpx.Response, base_url: str) -> str:
    location = response.headers.get("location", "")
    if response.status_code not in REDIRECT_STATUS_CODES or not location:
        raise MercedesAuthError(
            f"Authorization code not found in redirect URL (status={response.status_code})"
        )
    redirect_url = urllib.parse.urljoin(base_url, location)
    return _extract_code(redirect_url)


def _extract_code(redirect_url: str) -> str:
    parsed = urllib.parse.urlparse(redirect_url)
    params = urllib.parse.parse_qs(parsed.query)
    error = params.get("error", [None])[0]
    if error:
        description = params.get("error_description", [error])[0]
        raise MercedesAuthError(f"OAuth error: {description}")
    code = params.get("code", [None])[0]
    if not code:
        raise MercedesAuthError("Authorization code not found in redirect URL")
    return code


def _mobile_safari_headers(region: str, *, include_referer: bool = True) -> dict[str, str]:
    base = login_base_url(region)
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": base,
        "accept-language": "de-DE,de;q=0.9",
        "user-agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8_3 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6.6 Mobile/15E148 Safari/604.1"
        ),
    }
    if include_referer:
        headers["referer"] = f"{base}/ciam/auth/login"
    return headers
