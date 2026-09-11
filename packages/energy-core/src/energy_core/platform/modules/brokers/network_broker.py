"""Network broker for isolated modules."""



from __future__ import annotations



import logging

from urllib.parse import urljoin, urlparse



import httpx



from energy_core.config import Settings

from energy_core.platform.modules.distribution.types import ArtifactSourceType, DistributionError

from energy_core.platform.modules.distribution.url_policy import validate_artifact_url



logger = logging.getLogger(__name__)



MAX_REDIRECTS = 3





class NetworkBroker:

    def __init__(self, settings: Settings) -> None:

        self._settings = settings

        self._allowed_hosts: dict[tuple[str, int], set[str]] = {}



    def allow_host(self, *, module_id: str, site_id: int, host: str) -> None:

        key = (module_id, site_id)

        self._allowed_hosts.setdefault(key, set()).add(host.lower())



    def clear(self) -> None:

        self._allowed_hosts.clear()



    def _validate_url(self, url: str, *, permissions: tuple[str, ...]) -> None:

        if "network.local" in permissions:

            raise PermissionError("network.local denied by default policy")

        try:

            validate_artifact_url(url, source=ArtifactSourceType.PUBLIC, require_https=True)

        except DistributionError as exc:

            raise ValueError(str(exc)) from exc



    def _assert_allowlisted(self, *, module_id: str, site_id: int, url: str) -> None:

        parsed = urlparse(url)

        host = (parsed.hostname or "").lower()

        allowed = self._allowed_hosts.get((module_id, site_id), set())

        if host not in allowed:

            raise ValueError(f"host not allowlisted: {host}")



    async def request(

        self,

        *,

        runtime_instance_id: str,

        module_id: str,

        site_id: int,

        url: str,

        method: str = "GET",

        permissions: tuple[str, ...],

        headers: dict[str, str] | None = None,

        body: bytes | None = None,

    ) -> dict:

        if "network.external" not in permissions and "network.local" not in permissions:

            raise PermissionError("network permission required")

        if "network.local" in permissions:

            raise PermissionError("network.local denied")

        self._validate_url(url, permissions=permissions)

        self._assert_allowlisted(module_id=module_id, site_id=site_id, url=url)

        async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:

            current_url = url

            response: httpx.Response | None = None

            for _ in range(MAX_REDIRECTS + 1):

                self._validate_url(current_url, permissions=permissions)

                self._assert_allowlisted(module_id=module_id, site_id=site_id, url=current_url)

                response = await client.request(method, current_url, headers=headers, content=body)

                if response.is_redirect:

                    location = response.headers.get("location")

                    if not location:

                        raise ValueError("redirect without location header")

                    current_url = urljoin(current_url, location)

                    continue

                break

            else:

                raise ValueError("too many redirects")

        assert response is not None

        logger.info("network.request runtime=%s url=%s status=%s", runtime_instance_id, url, response.status_code)

        return {"status_code": response.status_code, "body": response.text[:65536]}


