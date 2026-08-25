"""Device token helper tests."""

from energy_core.auth.device_tokens import (
    extract_lookup_prefix,
    generate_device_token,
    verify_token,
)


def test_generate_and_verify_token():
    generated = generate_device_token()
    assert generated.token.startswith("emic_")
    assert generated.token_prefix == generated.token[:12]
    assert verify_token(generated.token, generated.token_hash)


def test_extract_lookup_prefix_rejects_invalid():
    assert extract_lookup_prefix("bad-token") is None
