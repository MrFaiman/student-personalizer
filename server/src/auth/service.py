import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, Request
from jose import JWTError
from sqlmodel import Session, select

from ..audit.service import log_event
from ..constants import INACTIVITY_TIMEOUT_MINUTES
from .models import PasswordHistory, User, UserRole, UserSession
from .password import (
    PASSWORD_HISTORY_DEPTH,
    hash_password,
    password_in_history,
    validate_password_policy,
    verify_password,
)
from .schemas import ChangePasswordRequest, CreateUserRequest, LoginRequest, TokenResponse
from .tokens import create_access_token, create_refresh_token, decode_refresh_token

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def create_user(self, req: CreateUserRequest) -> User:
        existing = self.session.exec(select(User).where(User.email == req.email)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        errors = validate_password_policy(req.password)
        if errors:
            raise HTTPException(status_code=422, detail={"password_errors": errors})

        user = User(
            email=req.email.lower().strip(),
            display_name=req.display_name,
            hashed_password=hash_password(req.password),
            role=req.role,
            must_change_password=req.must_change_password,
        )
        self.session.add(user)
        self.session.flush()

        # Seed password history
        history = PasswordHistory(user_id=user.id, hashed_password=user.hashed_password)
        self.session.add(history)
        self.session.commit()
        self.session.refresh(user)
        logger.info("user_created", extra={"user_id": str(user.id), "email": user.email, "role": user.role})
        return user

    def login(self, req: LoginRequest, request: Request | None = None) -> TokenResponse:
        user = self.session.exec(select(User).where(User.email == req.email.lower().strip())).first()

        ip = request.client.host if request and request.client else None
        ua = request.headers.get("user-agent") if request else None

        if not user or not user.is_active:
            logger.warning("login_failed_unknown", extra={"email": req.email})
            log_event(self.session, action="login", user_email=req.email, success=False, ip_address=ip, user_agent=ua, detail={"reason": "unknown email"})
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check lockout - normalise stored datetime (SQLite stores naive, PostgreSQL stores aware)
        if user.locked_until:
            locked_until = user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until
            if locked_until > _utcnow():
                logger.warning("login_blocked_lockout", extra={"user_id": str(user.id)})
                log_event(self.session, action="login", user_id=user.id, user_email=user.email, success=False, ip_address=ip, user_agent=ua, detail={"reason": "account locked"})
                raise HTTPException(status_code=429, detail="Account is temporarily locked. Please try again later.")

        if not verify_password(req.password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                from datetime import timedelta
                user.locked_until = _utcnow().replace(tzinfo=None) + timedelta(minutes=LOCKOUT_MINUTES)
                logger.warning("login_account_locked", extra={"user_id": str(user.id)})
            self.session.add(user)
            self.session.commit()
            log_event(self.session, action="login", user_id=user.id, user_email=user.email, success=False, ip_address=ip, user_agent=ua, detail={"reason": "wrong password"})
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Successful login, reset failure counter
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = _utcnow()
        self.session.add(user)

        access_token, jti, expires_at = create_access_token(user.id, user.role.value)
        refresh_token, _ = create_refresh_token(user.id, jti)

        session = UserSession(
            user_id=user.id,
            token_jti=jti,
            expires_at=expires_at,
            ip_address=ip,
            user_agent=ua,
        )
        self.session.add(session)
        self.session.commit()

        log_event(self.session, action="login", user_id=user.id, user_email=user.email, success=True, ip_address=ip, user_agent=ua)
        logger.info("login_success", extra={"user_id": str(user.id), "role": user.role, "ip": ip})
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_refresh_token(refresh_token)
        except JWTError:
            raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

        user_id = UUID(payload["sub"])
        jti = payload["jti"]

        session = self.session.exec(
            select(UserSession).where(UserSession.token_jti == jti, UserSession.is_revoked == False)  # noqa: E712
        ).first()

        if not session:
            raise HTTPException(status_code=401, detail="Session expired or revoked")

        # Check inactivity timeout
        inactive_minutes = (_utcnow() - session.last_activity.replace(tzinfo=timezone.utc)).total_seconds() / 60
        if inactive_minutes > INACTIVITY_TIMEOUT_MINUTES:
            session.is_revoked = True
            self.session.add(session)
            self.session.commit()
            raise HTTPException(status_code=401, detail="Session expired due to inactivity")

        user = self.session.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        # Revoke old session, issue new tokens
        session.is_revoked = True
        self.session.add(session)

        new_access, new_jti, expires_at = create_access_token(user.id, user.role.value)
        new_refresh, _ = create_refresh_token(user.id, new_jti)

        new_session = UserSession(
            user_id=user.id,
            token_jti=new_jti,
            expires_at=expires_at,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
        )
        self.session.add(new_session)
        self.session.commit()

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    def logout(self, jti: str) -> None:
        session = self.session.exec(
            select(UserSession).where(UserSession.token_jti == jti)
        ).first()
        if session:
            session.is_revoked = True
            self.session.add(session)
            self.session.commit()
            log_event(self.session, action="logout", user_id=session.user_id, success=True)
        logger.info("logout", extra={"jti": jti})

    def change_password(self, user: User, req: ChangePasswordRequest) -> None:
        if not verify_password(req.current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        errors = validate_password_policy(req.new_password)
        if errors:
            raise HTTPException(status_code=422, detail={"password_errors": errors})

        history = self.session.exec(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.created_at.desc())  # type: ignore[arg-type]
            .limit(PASSWORD_HISTORY_DEPTH)
        ).all()

        if password_in_history(req.new_password, [h.hashed_password for h in history]):
            raise HTTPException(status_code=422, detail="Cannot reuse one of the most recent passwords")

        new_hash = hash_password(req.new_password)
        user.hashed_password = new_hash
        user.must_change_password = False
        user.updated_at = _utcnow()
        self.session.add(user)

        self.session.add(PasswordHistory(user_id=user.id, hashed_password=new_hash))
        self.session.commit()
        logger.info("password_changed", extra={"user_id": str(user.id)})

    def admin_reset_password(self, target_user: User, new_password: str, must_change: bool = True) -> None:
        errors = validate_password_policy(new_password)
        if errors:
            raise HTTPException(status_code=422, detail={"password_errors": errors})
        new_hash = hash_password(new_password)
        target_user.hashed_password = new_hash
        target_user.must_change_password = must_change
        target_user.updated_at = _utcnow()
        self.session.add(target_user)
        self.session.add(PasswordHistory(user_id=target_user.id, hashed_password=new_hash))
        # Revoke all sessions for this user
        sessions = self.session.exec(
            select(UserSession).where(UserSession.user_id == target_user.id, UserSession.is_revoked == False)  # noqa: E712
        ).all()
        for s in sessions:
            s.is_revoked = True
            self.session.add(s)
        self.session.commit()

    def ensure_default_admin(self) -> None:
        """Create a default admin if no users exist."""
        count = self.session.exec(select(User)).first()
        if count is None:
            import os
            default_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@1234!")
            admin = User(
                email="admin@school.local",
                display_name="מנהל מערכת",
                hashed_password=hash_password(default_pass),
                role=UserRole.admin,
                must_change_password=True,
            )
            self.session.add(admin)
            self.session.add(PasswordHistory(user_id=admin.id, hashed_password=admin.hashed_password))
            self.session.commit()
            logger.warning(
                "default_admin_created",
                extra={"email": admin.email, "note": "Change password immediately"},
            )
