"""Tests for inverter read-only guard."""

import pytest

from energy_core.inverter.guard import InverterControlForbiddenError, assert_inverter_read_only, guard_inverter_client


def test_assert_inverter_read_only_blocks_write_operations():
    with pytest.raises(InverterControlForbiddenError):
        assert_inverter_read_only(operation="write_register")
    with pytest.raises(InverterControlForbiddenError):
        assert_inverter_read_only(operation="set_operating_mode")


def test_assert_inverter_read_only_allows_read_operations():
    assert_inverter_read_only(operation="read_register") is None


def test_guard_inverter_client_blocks_sync_writes():
    class Client:
        def read_register(self, address: int) -> int:
            return 1

        def write_register(self, address: int, value: int) -> None:
            self.last = value

    proxy = guard_inverter_client(Client())
    assert proxy.read_register(1) == 1
    with pytest.raises(InverterControlForbiddenError):
        proxy.write_register(1, 2)


def test_virtual_evse_modules_do_not_import_modbus():
    import energy_core.virtual_evse.reporter as reporter
    import energy_core.virtual_evse.semp_payloads as payloads

    for module in (reporter, payloads):
        source = module.__file__ or ""
        assert "modbus" not in source.lower()
