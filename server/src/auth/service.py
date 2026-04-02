import logging
from datetime import timezone
from uuid import UUID

from fastapi import HTTPException, Request
from jose import JWTError
from sqlalchemy.exc import ProgrammingError
from sqlmodel import Session, select

from ..audit.service import log_event
from ..constants import INACTIVITY_TIMEOUT_MINUTES
from ..utils.clock import utc_now
from .models import (
    PasswordHistory,
    Permission,
    Role,
    RolePermission,
    RoleScope,
    User,
    UserRole,
    UserRoleLink,
    UserSchoolMembership,
    UserSession,
)
from .password import (
    PASSWORD_HISTORY_DEPTH,
    hash_password,
    password_in_history,
    validate_password_policy,
    verify_password,
)
from .permissions import ALL_PERMISSION_KEYS, PermissionKey
from .schemas import ChangePasswordRequest, CreateUserRequest, LoginRequest, MfaChallengeResponse, TokenResponse
from .tokens import create_access_token, create_mfa_token, create_refresh_token, decode_refresh_token

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


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
            school_id=req.school_id,
            school_name=req.school_name,
        )
        self.session.add(user)
        self.session.flush()

        # If a school was provided, seed membership for multi-school support.
        if user.school_id is not None:
            self.session.add(
                UserSchoolMembership(
                    user_id=user.id,
                    school_id=user.school_id,
                    school_name=user.school_name,
                )
            )

        # Seed password history
        history = PasswordHistory(user_id=user.id, hashed_password=user.hashed_password)
        self.session.add(history)
        self.session.commit()
        self.session.refresh(user)
        logger.info("user_created", extra={"user_id": str(user.id), "email": user.email, "role": user.role})
        return user

    def login(self, req: LoginRequest, request: Request | None = None) -> TokenResponse | MfaChallengeResponse:
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
            if locked_until > utc_now():
                logger.warning("login_blocked_lockout", extra={"user_id": str(user.id)})
                log_event(self.session, action="login", user_id=user.id, user_email=user.email, success=False, ip_address=ip, user_agent=ua, detail={"reason": "account locked"})
                raise HTTPException(status_code=429, detail="Account is temporarily locked. Please try again later.")

        if not verify_password(req.password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                from datetime import timedelta
                user.locked_until = utc_now().replace(tzinfo=None) + timedelta(minutes=LOCKOUT_MINUTES)
                logger.warning("login_account_locked", extra={"user_id": str(user.id)})
            self.session.add(user)
            self.session.commit()
            log_event(self.session, action="login", user_id=user.id, user_email=user.email, success=False, ip_address=ip, user_agent=ua, detail={"reason": "wrong password"})
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Successful login, reset failure counter
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = utc_now()
        self.session.add(user)
        self.session.commit()  # persist counter reset before returning

        # MFA gate: if the user has MFA enabled, issue a short-lived pending token
        # instead of full access/refresh tokens.  The client must complete the
        # MFA challenge at POST /api/auth/mfa/challenge.
        if user.mfa_enabled:
            mfa_token = create_mfa_token(user.id)
            log_event(self.session, action="login_mfa_required", user_id=user.id, user_email=user.email, success=True, ip_address=ip, user_agent=ua)
            return MfaChallengeResponse(mfa_token=mfa_token)

        access_token, jti, expires_at = create_access_token(
            user.id, user.role.value, mfa_verified=False, school_id=user.school_id
        )
        refresh_token, _ = create_refresh_token(user.id, jti, school_id=user.school_id)

        session = UserSession(
            user_id=user.id,
            token_jti=jti,
            expires_at=expires_at,
            ip_address=ip,
            user_agent=ua,
            mfa_verified=False,
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
        school_id = payload.get("school_id")

        session = self.session.exec(
            select(UserSession).where(UserSession.token_jti == jti, UserSession.is_revoked == False)  # noqa: E712
        ).first()

        if not session:
            raise HTTPException(status_code=401, detail="Session expired or revoked")

        # Check inactivity timeout
        inactive_minutes = (utc_now() - session.last_activity.replace(tzinfo=timezone.utc)).total_seconds() / 60
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

        # Preserve mfa_verified state across token refresh
        new_access, new_jti, expires_at = create_access_token(
            user.id, user.role.value,
            mfa_verified=session.mfa_verified,
            school_id=school_id if isinstance(school_id, int) else user.school_id,
        )
        new_refresh, _ = create_refresh_token(
            user.id,
            new_jti,
            school_id=school_id if isinstance(school_id, int) else user.school_id,
        )

        new_session = UserSession(
            user_id=user.id,
            token_jti=new_jti,
            expires_at=expires_at,
            mfa_verified=session.mfa_verified,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
        )
        self.session.add(new_session)
        self.session.commit()

        log_event(
            self.session,
            action="refresh",
            user_id=user.id,
            user_email=user.email,
            success=True,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            detail={"school_id": school_id if isinstance(school_id, int) else None},
        )
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
        user.updated_at = utc_now()
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
        target_user.updated_at = utc_now()
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
        log_event(
            self.session,
            action="admin_reset_password",
            user_id=target_user.id,
            user_email=target_user.email,
            success=True,
            detail={"must_change_password": must_change},
        )

    def ensure_default_admin(self) -> None:
        """Ensure at least one privileged user exists."""
        count = self.session.exec(select(User)).first()
        if count is None:
            import os
            admin_email = os.getenv("ADMIN_EMAIL", "admin@school.local").lower().strip()
            default_pass = os.getenv("ADMIN_PASSWORD") or os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@1234!")
            admin = User(
                email=admin_email,
                display_name="Administrator",
                hashed_password=hash_password(default_pass),
                role=UserRole.system_admin,
                must_change_password=True,
            )
            self.session.add(admin)
            self.session.add(PasswordHistory(user_id=admin.id, hashed_password=admin.hashed_password))
            self.session.commit()
            logger.warning(
                "default_admin_created",
                extra={"email": admin.email, "note": "Change password immediately"},
            )

    def ensure_rbac_seed(self) -> None:
        """Idempotently seed baseline RBAC roles and backfill assignments.

        This is a transitional bootstrap:
        - Creates normalized Role rows matching the legacy User.role enum values.
        - Backfills one UserRoleLink per user to preserve behavior while router/service
          enforcement is migrated to permission checks.
        """
        # 1) Seed baseline roles (normalized RBAC)
        #
        # For PostgreSQL environments, schema is managed by Alembic migrations.
        # If migrations were not applied yet, fail fast with a clear message.
        try:
            existing_roles = {r.name: r for r in self.session.exec(select(Role)).all()}
        except ProgrammingError as exc:
            raise RuntimeError(
                "RBAC tables are missing in the database. Ensure the server can create tables on startup (init_db) or wipe/recreate the DB."
            ) from exc
        baseline: list[tuple[str, RoleScope]] = [
            (UserRole.super_admin.value, RoleScope.global_),
            (UserRole.system_admin.value, RoleScope.global_),
            (UserRole.school_admin.value, RoleScope.school),
            (UserRole.teacher.value, RoleScope.school),
            (UserRole.read_only.value, RoleScope.school),
        ]

        created = False
        for name, scope in baseline:
            if name not in existing_roles:
                role = Role(name=name, scope=scope)
                self.session.add(role)
                created = True

        if created:
            self.session.commit()

        roles = {r.name: r for r in self.session.exec(select(Role)).all()}

        # 2) Seed baseline permissions + role mappings
        existing_perms = {p.key: p for p in self.session.exec(select(Permission)).all()}
        for key in ALL_PERMISSION_KEYS:
            if key not in existing_perms:
                self.session.add(Permission(key=key))
                created = True
        if created:
            self.session.commit()

        perms = {p.key: p for p in self.session.exec(select(Permission)).all()}

        def grant(role_name: str, keys: set[str]) -> None:
            role = roles.get(role_name)
            if not role:
                return
            for k in keys:
                perm = perms.get(k)
                if not perm:
                    continue
                exists = self.session.exec(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    )
                ).first()
                if exists:
                    continue
                self.session.add(RolePermission(role_id=role.id, permission_id=perm.id))

        all_keys = set(ALL_PERMISSION_KEYS)
        grant(UserRole.super_admin.value, all_keys)
        grant(UserRole.system_admin.value, all_keys)

        grant(
            UserRole.school_admin.value,
            {
                PermissionKey.students_read.value,
                PermissionKey.students_write.value,
                PermissionKey.ingestion_upload.value,
                PermissionKey.ingestion_logs_read.value,
                PermissionKey.ingestion_delete.value,
                PermissionKey.analytics_read.value,
                PermissionKey.ml_train.value,
                PermissionKey.admin_users_read.value,
                PermissionKey.admin_users_write.value,
                PermissionKey.config_read.value,
                PermissionKey.config_write.value,
            },
        )
        grant(
            UserRole.teacher.value,
            {
                PermissionKey.students_read.value,
                PermissionKey.students_write.value,
                PermissionKey.ingestion_logs_read.value,
                PermissionKey.analytics_read.value,
                PermissionKey.config_read.value,
            },
        )
        grant(
            UserRole.read_only.value,
            {
                PermissionKey.students_read.value,
                PermissionKey.ingestion_logs_read.value,
                PermissionKey.analytics_read.value,
                PermissionKey.config_read.value,
            },
        )

        self.session.commit()

        # 3) Backfill user_role links from legacy user.role
        users = self.session.exec(select(User)).all()
        for u in users:
            role = roles.get(u.role.value)
            if not role:
                continue

            already = self.session.exec(
                select(UserRoleLink).where(
                    UserRoleLink.user_id == u.id,
                    UserRoleLink.role_id == role.id,
                    UserRoleLink.school_id.is_(None),
                )
            ).first()
            if already:
                continue

            self.session.add(UserRoleLink(user_id=u.id, role_id=role.id, school_id=None))
            created = True

        if created:
            self.session.commit()
