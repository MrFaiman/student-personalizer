"""MFA / TOTP implementation (MoE section 4.2).

Flow:
  1. POST /api/auth/mfa/setup     → generates secret + provisioning URI, stores pending secret
  2. POST /api/auth/mfa/verify    → validates TOTP code, activates MFA, returns plaintext backup codes
  3. POST /api/auth/mfa/disable   → admin or self can disable (requires current TOTP code)
  4. POST /api/auth/login         → when mfa_enabled, returns {mfa_required: true, mfa_token: <jwt>}
  5. POST /api/auth/mfa/challenge → submit TOTP or backup code, receive full access+refresh tokens

Backup codes:
  - 8 codes, each 10 chars (hex), stored as Argon2id hashes in mfa_backup_codes (JSON array)
  - Each code is single-use; used codes are removed from the array
"""

import json
import logging
import secrets

import pyotp
from fastapi import HTTPException

from ..auth.password import hash_password, verify_password
from .models import User

logger = logging.getLogger(__name__)

BACKUP_CODE_COUNT = 8
BACKUP_CODE_LENGTH = 10  # hex chars → 5 bytes entropy each
APP_NAME = "StudentPersonalizer"


def generate_totp_secret() -> str:
    """Generate a new base32-encoded TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, user_email: str) -> str:
    """Return an otpauth:// URI suitable for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name=APP_NAME)


def verify_totp(secret: str, code: str) -> bool:
    """Validate a 6-digit TOTP code with ±1 window tolerance."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes() -> tuple[list[str], list[str]]:
    """Return (plaintext_codes, hashed_codes).

    Plaintext codes are shown once to the user; hashed codes are stored in DB.
    """
    plaintext = [secrets.token_hex(BACKUP_CODE_LENGTH // 2) for _ in range(BACKUP_CODE_COUNT)]
    hashed = [hash_password(code) for code in plaintext]
    return plaintext, hashed


def consume_backup_code(user: User, code: str) -> bool:
    """Check if `code` matches a stored backup code and remove it if so.

    Returns True if the code was valid and consumed, False otherwise.
    """
    if not user.mfa_backup_codes:
        return False
    stored: list[str] = json.loads(user.mfa_backup_codes)
    for i, hashed in enumerate(stored):
        if verify_password(code, hashed):
            stored.pop(i)
            user.mfa_backup_codes = json.dumps(stored)
            return True
    return False


def setup_mfa(user: User) -> tuple[str, str]:
    """Generate a new TOTP secret and provisioning URI.

    The secret is stored on the user record but mfa_enabled stays False until
    verify_mfa_setup() is called successfully.

    Returns (secret, provisioning_uri).
    """
    secret = generate_totp_secret()
    user.mfa_secret = secret
    # mfa_enabled stays False until the user proves they can generate a valid code
    return secret, get_provisioning_uri(secret, user.email)


def verify_mfa_setup(user: User, code: str) -> list[str]:
    """Confirm TOTP setup with the first code from the authenticator app.

    Activates MFA and returns plaintext backup codes (shown once).
    Raises HTTPException(400) if the code is wrong.
    """
    if not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA setup not initiated")
    if not verify_totp(user.mfa_secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    plaintext, hashed = generate_backup_codes()
    user.mfa_enabled = True
    user.mfa_backup_codes = json.dumps(hashed)
    logger.info("mfa_activated", extra={"user_id": str(user.id)})
    return plaintext


def check_mfa_code(user: User, code: str) -> None:
    """Validate a TOTP code or backup code for an MFA-enabled user.

    Raises HTTPException(401) if the code is invalid.
    Consumes the backup code if one was used.
    """
    if not user.mfa_secret or not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not configured for this user")

    if verify_totp(user.mfa_secret, code):
        return

    if consume_backup_code(user, code):
        logger.warning("mfa_backup_code_used", extra={"user_id": str(user.id)})
        return

    raise HTTPException(status_code=401, detail="Invalid MFA code")


def disable_mfa(user: User, code: str) -> None:
    """Disable MFA after verifying the current TOTP code or a backup code."""
    check_mfa_code(user, code)
    user.mfa_secret = None
    user.mfa_enabled = False
    user.mfa_backup_codes = None
    logger.info("mfa_disabled", extra={"user_id": str(user.id)})
