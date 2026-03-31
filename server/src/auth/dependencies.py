"""FastAPI dependencies for identity resolution and authorisation.

Chain:
  Bearer token  →  _get_token_payload()
                →  session revocation/activity check
                →  DB user fetch
                →  CurrentUser construction
                →  role / permission checks

Every protected route depends on get_current_user (or a require_* shortcut).
Routes that must mutate the User ORM record (change_password, mfa_setup …)
use get_db_user instead.
"""

from datetime import timezone
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session, select

from ..constants import INACTIVITY_TIMEOUT_MINUTES
from ..database import get_session
from ..utils.clock import utc_now
from .current_user import CurrentUser
from .models import User, UserRole, UserSession
from .tokens import decode_token

_bearer = HTTPBearer(auto_error=False)


def _get_token_payload(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> CurrentUser:
    """Resolve a Bearer token into a CurrentUser claims object.

    Steps
    -----
    1. Decode and validate JWT signature / expiry.
    2. Verify token type is "access" (not refresh / mfa_pending).
    3. Load the UserSession from DB - checks revocation.
    4. Enforce inactivity timeout; update last_activity.
    5. Load the User record - checks is_active.
    6. Build and return an immutable CurrentUser.
    """
    payload = _get_token_payload(credentials)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti", "")
    user_id = UUID(payload["sub"])

    # -- Session check --------------------------------------------------
    db_session = session.exec(
        select(UserSession).where(
            UserSession.token_jti == jti,
            UserSession.is_revoked == False,  # noqa: E712
        )
    ).first()

    if not db_session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    inactive_minutes = (utc_now() - db_session.last_activity.replace(tzinfo=timezone.utc)).total_seconds() / 60
    if inactive_minutes > INACTIVITY_TIMEOUT_MINUTES:
        db_session.is_revoked = True
        session.add(db_session)
        session.commit()
        raise HTTPException(status_code=401, detail="Session expired due to inactivity")

    db_session.last_activity = utc_now()
    session.add(db_session)
    session.commit()

    # -- User check -----------------------------------------------------
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # -- Build CurrentUser from JWT claims + DB fields ------------------
    school_id_claim = payload.get("school_id")
    if school_id_claim is None:
        school_id = user.school_id
    elif isinstance(school_id_claim, int):
        school_id = school_id_claim
    else:
        raise HTTPException(status_code=401, detail="Invalid school_id claim in token")

    return CurrentUser(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        mfa_enabled=user.mfa_enabled,
        mfa_verified=bool(payload.get("mfa_verified", False)),
        identity_provider=user.identity_provider,
        external_id=user.external_subject_id,
        school_id=school_id,
        school_name=user.school_name,
        session_jti=jti,
    )


def get_db_user(
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    """Fetch the User ORM record for the authenticated user.

    Use this only in auth-layer routes that need to mutate the user record
    (change_password, mfa_setup, etc.).  Business-logic routes should use
    get_current_user and work with the CurrentUser claims object.
    """
    user = session.get(User, current_user.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_role(*roles: UserRole):
    """Dependency factory - require the current user to have one of the given roles."""
    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _check


# Convenience shortcuts
require_admin = require_role(UserRole.admin)
require_teacher = require_role(UserRole.admin, UserRole.teacher)
require_viewer = require_role(UserRole.admin, UserRole.teacher, UserRole.viewer)
