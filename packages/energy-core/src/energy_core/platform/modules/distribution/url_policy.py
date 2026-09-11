"""URL validation and SSRF defenses for remote artifact download."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from energy_core.platform.modules.distribution.types import (
    ArtifactSourceType,
    DistributionError,
    DistributionErrorCode,
)


FORBIDDEN_SCHEMES = frozenset({"file", "ftp", "data", "gopher", "javascript", "mailto"})
METADATA_IP = ipaddress.ip_address("169.254.169.254")


def _is_forbidden_ip(addr: ipaddress._BaseAddress) -> bool:
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
        or addr.is_reserved
        or addr == METADATA_IP
    )


def validate_artifact_url(
    url: str,
    *,
    source: ArtifactSourceType,
    require_https: bool = True,
    allowed_ports: frozenset[int] | None = None,
    internal_cidrs: tuple[str, ...] = (),
) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() in FORBIDDEN_SCHEMES:
        raise DistributionError(f"Forbidden URL scheme: {parsed.scheme}", code=DistributionErrorCode.ARTIFACT_URL_INVALID)
    host = parsed.hostname
    if not host:
        raise DistributionError("Missing hostname", code=DistributionErrorCode.ARTIFACT_URL_INVALID)
    if require_https and parsed.scheme.lower() != "https":
        internal_http_hosts = {"caddy", "backend", "localhost", "127.0.0.1"}
        if not (source == ArtifactSourceType.INTERNAL and host.lower() in internal_http_hosts):
            raise DistributionError("HTTPS required for artifact download", code=DistributionErrorCode.ARTIFACT_URL_INVALID)
    if parsed.username or parsed.password:
        raise DistributionError("Embedded credentials in URL rejected", code=DistributionErrorCode.ARTIFACT_URL_INVALID)
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    ports = allowed_ports or frozenset({443})
    test_host = host.lower() in {"127.0.0.1", "localhost"}
    if source == ArtifactSourceType.PUBLIC and port not in ports:
        if not (not require_https and test_host):
            raise DistributionError(f"Port {port} not allowed for PUBLIC source", code=DistributionErrorCode.ARTIFACT_URL_INVALID)

    allow_private = source in {ArtifactSourceType.INTERNAL, ArtifactSourceType.ORG, ArtifactSourceType.LOCAL}
    if source == ArtifactSourceType.PUBLIC and not require_https and test_host:
        return
    if host.lower() in {"localhost"} or host.endswith(".localhost"):
        if not allow_private:
            raise DistributionError("localhost blocked for PUBLIC source", code=DistributionErrorCode.ARTIFACT_SSRF_BLOCKED)
        return

    try:
        literal = ipaddress.ip_address(host)
        if _is_forbidden_ip(literal):
            if not allow_private or not _ip_in_cidrs(literal, internal_cidrs):
                raise DistributionError("Forbidden IP destination", code=DistributionErrorCode.ARTIFACT_SSRF_BLOCKED)
        return
    except ValueError:
        pass

    resolved = _resolve_all(host)
    for addr in resolved:
        if _is_forbidden_ip(addr):
            if allow_private and _ip_in_cidrs(addr, internal_cidrs):
                continue
            raise DistributionError(
                f"Hostname {host} resolves to forbidden address {addr}",
                code=DistributionErrorCode.ARTIFACT_SSRF_BLOCKED,
            )


def _resolve_all(hostname: str) -> list[ipaddress._BaseAddress]:
    results: list[ipaddress._BaseAddress] = []
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if family == socket.AF_INET:
                results.append(ipaddress.ip_address(sockaddr[0]))
            elif family == socket.AF_INET6:
                results.append(ipaddress.ip_address(sockaddr[0]))
    except socket.gaierror as exc:
        raise DistributionError(f"DNS resolution failed for {hostname}", code=DistributionErrorCode.ARTIFACT_SSRF_BLOCKED) from exc
    if not results:
        raise DistributionError(f"No addresses for {hostname}", code=DistributionErrorCode.ARTIFACT_SSRF_BLOCKED)
    return results


def _ip_in_cidrs(addr: ipaddress._BaseAddress, cidrs: tuple[str, ...]) -> bool:
    for cidr in cidrs:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False
