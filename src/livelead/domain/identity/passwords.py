"""PBKDF2 password hashing helpers (US-027).

Pure functions, no I/O. The application layer wires these into the
auth service.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass


PBKDF2_ALGO = "sha256"
PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16
HASH_BYTES = 32

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256


@dataclass(frozen=True, slots=True)
class PasswordMaterial:
    """Persisted password material. The cleartext password is never stored."""

    password_hash: str  # base64-encoded
    salt: str  # base64-encoded
    iterations: int

    def constant_time_eq(self, candidate_hash_b64: str) -> bool:
        try:
            candidate = base64.b64decode(candidate_hash_b64, validate=True)
        except (ValueError, TypeError):
            return False
        expected = base64.b64decode(self.password_hash, validate=True)
        return hmac.compare_digest(candidate, expected)


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


def validate_password_shape(password: str) -> None:
    if not isinstance(password, str):
        raise ValueError("password must be a string")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("password too short")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("password too long")
    if not password.strip():
        raise ValueError("password cannot be blank")


def generate_salt() -> str:
    return _b64encode(os.urandom(SALT_BYTES))


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> PasswordMaterial:
    validate_password_shape(password)
    salt = os.urandom(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(PBKDF2_ALGO, password.encode("utf-8"), salt, iterations)
    return PasswordMaterial(
        password_hash=_b64encode(derived),
        salt=_b64encode(salt),
        iterations=iterations,
    )


def hash_password_with_salt(
    password: str, *, salt_b64: str, iterations: int = PBKDF2_ITERATIONS
) -> PasswordMaterial:
    validate_password_shape(password)
    salt = _b64decode(salt_b64)
    derived = hashlib.pbkdf2_hmac(PBKDF2_ALGO, password.encode("utf-8"), salt, iterations)
    return PasswordMaterial(
        password_hash=_b64encode(derived),
        salt=salt_b64,
        iterations=iterations,
    )


def verify_password(password: str, material: PasswordMaterial) -> bool:
    if not isinstance(password, str) or not password:
        return False
    try:
        derived = hashlib.pbkdf2_hmac(
            PBKDF2_ALGO,
            password.encode("utf-8"),
            _b64decode(material.salt),
            material.iterations,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(_b64encode(derived), material.password_hash)


def email_is_password(email: str, password: str) -> bool:
    return normalize_email(email) == password.strip().lower()


__all__ = [
    "PBKDF2_ALGO",
    "PBKDF2_ITERATIONS",
    "SALT_BYTES",
    "HASH_BYTES",
    "MIN_PASSWORD_LENGTH",
    "MAX_PASSWORD_LENGTH",
    "PasswordMaterial",
    "normalize_email",
    "validate_password_shape",
    "generate_salt",
    "hash_password",
    "hash_password_with_salt",
    "verify_password",
    "email_is_password",
]
