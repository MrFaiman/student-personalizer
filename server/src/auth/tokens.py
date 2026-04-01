from datetime import datetime, timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt

from ..constants import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY, REFRESH_TOKEN_EXPIRE_HOURS
from ..utils.clock import utc_now


def create_access_token(
    user_id: UUID,
    role: str,
    *,
    mfa_verified: bool = False,
    school_id: int | None = None,
) -> tuple[str, str, datetime]:
    """Return (token, jti, expires_at).

    Claims embedded in the JWT:
      sub           - user UUID
      role          - coarse-grained role string
      jti           - session identifier (used for revocation)
      mfa_verified  - True if MFA was completed in this session
    school_id     - Mashov semel (omitted when None)
      type          - "access"
    """
    jti = str(uuid4())
    expires_at = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "exp": expires_at,
        "type": "access",
        "mfa_verified": mfa_verified,
    }
    if school_id is not None:
        payload["school_id"] = school_id
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, jti, expires_at


def create_refresh_token(user_id: UUID, jti: str, *, school_id: int | None = None) -> tuple[str, datetime]:
    """Return (token, expires_at). Shares JTI with the access token session.

    Includes school_id so token refresh can preserve the selected school scope
    without requiring DB schema migrations on the sessions table.
    """
    expires_at = utc_now() + timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "exp": expires_at,
        "type": "refresh",
    }
    if school_id is not None:
        payload["school_id"] = school_id
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expires_at


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def decode_refresh_token(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    return payload


def create_mfa_token(user_id: UUID) -> str:
    """Short-lived token (5 min) issued after password login when MFA is required.

    The client submits this token alongside the TOTP code to complete login.
    It carries type='mfa_pending' so it cannot be used as an access token.
    """
    expires_at = utc_now() + timedelta(minutes=5)
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "type": "mfa_pending",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_mfa_token(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("type") != "mfa_pending":
        raise JWTError("Not an MFA pending token")
    return payload
