"""Password hashing tests."""

from energy_core.auth.passwords import hash_password, validate_password_policy, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("SecurePassphrase123")
    assert verify_password("SecurePassphrase123", hashed)
    assert not verify_password("wrong", hashed)


def test_validate_password_policy_rejects_short():
    assert validate_password_policy("short") is not None


def test_validate_password_policy_accepts_long():
    assert validate_password_policy("long-passphrase-ok") is None
