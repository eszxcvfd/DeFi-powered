import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("livelead.secrets")

REDACTED = "***REDACTED***"


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    return REDACTED


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


class SecretVault:
    def __init__(self, master_secret: str) -> None:
        self._fernet = Fernet(_derive_fernet_key(master_secret))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("invalid secret ciphertext") from exc

    def safe_log_fields(self, *, has_secret: bool) -> dict[str, str]:
        return {"secret": REDACTED if has_secret else "(none)"}