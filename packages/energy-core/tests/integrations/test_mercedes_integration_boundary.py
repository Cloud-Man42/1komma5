"""Tests for Mercedes integration boundary modules."""

from __future__ import annotations


def test_mercedes_auth_facade_reexports_errors():
    from energy_core.integrations.mercedes.auth import MercedesAuthError, MercedesTwoFactorUnsupported
    from energy_core.vehicles.mercedes.auth.errors import MercedesAuthError as DirectAuthError

    assert MercedesAuthError is DirectAuthError
    assert issubclass(MercedesTwoFactorUnsupported, MercedesAuthError)


def test_mercedes_commands_facade_reexports_builders():
    from energy_core.integrations.mercedes.commands import build_set_target_soc_command
    from energy_core.vehicles.mercedes.commands.builder import build_set_target_soc_command as direct

    assert build_set_target_soc_command is direct


def test_attribute_observation_is_vendor_neutral():
    from energy_core.vehicles.abstractions.attribute_observation import AttributeObservation
    from energy_core.vehicles.mercedes.mapping.observer import AttributeObservation as observer_export

    assert AttributeObservation is observer_export
