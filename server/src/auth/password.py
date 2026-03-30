import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=1024 * 64,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

PASSWORD_MIN_LENGTH = 10
PASSWORD_HISTORY_DEPTH = 5


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def validate_password_policy(password: str) -> list[str]:
    """Return list of policy violations (empty = valid)."""
    errors: list[str] = []

    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        errors.append("Password must contain at least one special character")

    return errors


def password_in_history(plain: str, history_hashes: list[str]) -> bool:
    """Check if password matches any of the recent history."""
    for old_hash in history_hashes[-PASSWORD_HISTORY_DEPTH:]:
        if verify_password(plain, old_hash):
            return True
    return False
