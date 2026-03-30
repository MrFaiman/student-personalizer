from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session, select

from ..constants import INACTIVITY_TIMEOUT_MINUTES
from ..database import get_session
from .models import User, UserRole, UserSession
from .tokens import decode_token

_bearer = HTTPBearer(auto_error=False)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
) -> User:
    payload = _get_token_payload(credentials)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    user_id = UUID(payload["sub"])

    # Validate session is active and not timed out
    db_session = session.exec(
        select(UserSession).where(
            UserSession.token_jti == jti,
            UserSession.is_revoked == False,  # noqa: E712
        )
    ).first()

    if not db_session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    inactive_minutes = (_utcnow() - db_session.last_activity.replace(tzinfo=timezone.utc)).total_seconds() / 60
    if inactive_minutes > INACTIVITY_TIMEOUT_MINUTES:
        db_session.is_revoked = True
        session.add(db_session)
        session.commit()
        raise HTTPException(status_code=401, detail="הפגישה פגה עקב חוסר פעילות")

    # Refresh last_activity
    db_session.last_activity = _utcnow()
    session.add(db_session)
    session.commit()

    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_role(*roles: UserRole):
    """Dependency factory, require the current user to have one of the given roles."""
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check


# Convenience shortcuts
require_admin = require_role(UserRole.admin)
require_teacher = require_role(UserRole.admin, UserRole.teacher)
require_viewer = require_role(UserRole.admin, UserRole.teacher, UserRole.viewer)
