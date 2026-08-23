"""Tests for Charge Amps current parameter formatting."""

import pytest
from energy_core.chargers.charge_amps_web import _current_param


@pytest.mark.parametrize(
    ("amps", "expected"),
    [
        (16.0, 16),
        (10.4, 10),
        (10.6, 11),
        (0.0, 0),
        (6.0, 6),
    ],
)
def test_current_param_is_integer(amps, expected):
    assert _current_param(amps) == expected
    assert isinstance(_current_param(amps), int)
