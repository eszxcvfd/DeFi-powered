"""PBKDF2 password hashing helpers (US-027)."""

from __future__ import annotations

import base64

import pytest

from livelead.domain.identity import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    PasswordMaterial,
    email_is_password,
    generate_salt,
    hash_password,
    hash_password_with_salt,
    normalize_email,
    validate_password_shape,
    verify_password,
)


def test_hash_password_returns_unique_salts():
    a = hash_password("Hello-World-2026")
    b = hash_password("Hello-World-2026")
    assert a.salt != b.salt
    assert a.password_hash != b.password_hash


def test_hash_password_is_deterministic_for_same_salt():
    salt = generate_salt()
    a = hash_password_with_salt("Hello-World-2026", salt_b64=salt)
    b = hash_password_with_salt("Hello-World-2026", salt_b64=salt)
    assert a.password_hash == b.password_hash


def test_verify_password_returns_true_for_correct_password():
    material = hash_password("Hello-World-2026")
    assert verify_password("Hello-World-2026", material) is True


def test_verify_password_returns_false_for_wrong_password():
    material = hash_password("Hello-World-2026")
    assert verify_password("Hello-World-2026-x", material) is False


def test_verify_password_returns_false_for_empty_password():
    material = hash_password("Hello-World-2026")
    assert verify_password("", material) is False


def test_verify_password_returns_false_for_non_string():
    material = hash_password("Hello-World-2026")
    assert verify_password(None, material) is False  # type: ignore[arg-type]
    assert verify_password(12345, material) is False  # type: ignore[arg-type]


def test_validate_password_shape_rejects_short():
    with pytest.raises(ValueError):
        validate_password_shape("short")
    with pytest.raises(ValueError):
        validate_password_shape("a" * (MIN_PASSWORD_LENGTH - 1))


def test_validate_password_shape_rejects_overlong():
    with pytest.raises(ValueError):
        validate_password_shape("a" * (MAX_PASSWORD_LENGTH + 1))


def test_validate_password_shape_rejects_blank():
    with pytest.raises(ValueError):
        validate_password_shape("            ")


def test_normalize_email_lowercases_and_strips():
    assert normalize_email("  Alice@Example.com  ") == "alice@example.com"


def test_email_is_password_detects_email_like_password():
    assert email_is_password("alice@example.com", "Alice@Example.com") is True
    assert email_is_password("alice@example.com", "Other-Passphrase-2026") is False


def test_password_material_constant_time_eq_returns_true_for_same_hash():
    material = hash_password("Hello-World-2026")
    assert material.constant_time_eq(material.password_hash) is True


def test_password_material_constant_time_eq_returns_false_for_other_hash():
    material = hash_password("Hello-World-2026")
    other = hash_password("Other-Passphrase-2026")
    assert material.constant_time_eq(other.password_hash) is False


def test_password_material_constant_time_eq_returns_false_for_invalid_b64():
    material = hash_password("Hello-World-2026")
    assert material.constant_time_eq("not-base64-!!") is False


def test_hash_password_uses_expected_iteration_count():
    material = hash_password("Hello-World-2026")
    assert material.iterations >= 100_000


def test_salt_round_trip_is_base64():
    salt = generate_salt()
    decoded = base64.b64decode(salt.encode("ascii"), validate=True)
    assert len(decoded) == 16
