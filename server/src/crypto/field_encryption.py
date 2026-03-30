"""
AES-256-GCM field-level encryption for PII columns (MoE section 3.2).

Storage format: hex(iv) + ":" + hex(tag) + ":" + hex(ciphertext)
IV is 12 bytes (96-bit), tag is 16 bytes (128-bit).
Key must be exactly 32 bytes (base64-encoded in env var FIELD_ENCRYPTION_KEY).
"""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes | None:
    """Decode FIELD_ENCRYPTION_KEY from env. Returns None if not set (dev mode)."""
    from ..config import settings

    raw = settings.field_encryption_key
    if not raw:
        return None
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise RuntimeError("FIELD_ENCRYPTION_KEY must be a valid base64-encoded string") from exc
    if len(key) != 32:
        raise RuntimeError(f"FIELD_ENCRYPTION_KEY must decode to exactly 32 bytes (got {len(key)})")
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns hex-encoded 'iv:tag:ciphertext'."""
    key = _get_key()
    if key is None:
        return plaintext  # dev mode: no encryption

    iv = os.urandom(12)
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    # AESGCM appends the 16-byte tag to the ciphertext
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    return f"{iv.hex()}:{tag.hex()}:{ciphertext.hex()}"


def decrypt(stored: str) -> str:
    """Decrypt a stored 'iv:tag:ciphertext' string. Returns original plaintext."""
    key = _get_key()
    if key is None:
        return stored  # dev mode: passthrough

    # Handle values that were stored before encryption was enabled
    if ":" not in stored:
        return stored

    parts = stored.split(":", 2)
    if len(parts) != 3:
        return stored  # malformed, return as-is rather than crash

    try:
        iv = bytes.fromhex(parts[0])
        tag = bytes.fromhex(parts[1])
        ciphertext = bytes.fromhex(parts[2])
    except ValueError:
        return stored  # not encrypted (plaintext from before migration)

    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext + tag, None)
    return plaintext_bytes.decode("utf-8")


def hash_for_lookup(value: str) -> str:
    """
    HMAC-SHA256 of a value using HASH_PEPPER.
    Used for student_tz_hash to allow equality lookups on encrypted columns.
    Returns hex digest, or SHA-256(value) in dev mode (no pepper).
    """
    from ..config import settings

    pepper = settings.hash_pepper
    if not pepper:
        # Dev mode: deterministic hash without secret
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    return hmac.new(pepper.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
