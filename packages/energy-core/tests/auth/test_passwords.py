"""Password hashing tests."""

from energy_core.auth.passwords import hash_password, validate_password_policy, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("SecurePassphrase123")
    assert verify_password("SecurePassphrase123", hashed)
    assert not verify_password("wrong", hashed)


def test_validate_password_policy_rejects_empty():
    assert validate_password_policy("") is not None
    assert validate_password_policy("   ") is not None


def test_validate_password_policy_accepts_any_non_empty_length():
    assert validate_password_policy("short") is None
    assert validate_password_policy("long-passphrase-ok") is None
