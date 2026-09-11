"""network_hosts manifest validation tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.packages.errors import INVALID_MANIFEST, PackageError
from energy_core.platform.modules.packages.network_hosts import validate_network_hosts


def test_valid_network_hosts():
    validate_network_hosts(("home.sensibo.com", "api.example.com"))


@pytest.mark.parametrize(
    "hosts",
    [
        ("*.sensibo.com",),
        ("?",),
        (".example.com",),
        ("https://home.sensibo.com",),
        ("",),
    ],
)
def test_invalid_network_hosts(hosts):
    with pytest.raises(PackageError) as exc:
        validate_network_hosts(hosts)
    assert exc.value.code == INVALID_MANIFEST
