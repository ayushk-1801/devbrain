"""Fernet symmetric encryption for storing tenant secrets at rest."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    secret = os.getenv("PLATFORM_SECRET_KEY", "")
    if not secret:
        raise RuntimeError("PLATFORM_SECRET_KEY env var is required")
    # Derive a 32-byte key from whatever-length secret using SHA-256
    key_bytes = hashlib.sha256(secret.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_secrets(secrets: dict) -> str:
    """JSON-serialize and Fernet-encrypt a dict of secrets."""
    f = _get_fernet()
    plaintext = json.dumps(secrets).encode()
    return f.encrypt(plaintext).decode()


def decrypt_secrets(encrypted: str) -> dict:
    """Fernet-decrypt and JSON-parse secrets."""
    f = _get_fernet()
    plaintext = f.decrypt(encrypted.encode())
    return json.loads(plaintext)
