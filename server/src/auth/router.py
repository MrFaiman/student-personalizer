import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session, select

from ..audit.service import log_event
from ..database import get_session
from ..dependencies import require_write_access
from ..middleware.rate_limit import rate_limit
from .current_user import CurrentUser
from .dependencies import get_current_user, get_db_user, require_admin
from .mfa import check_mfa_code, disable_mfa, setup_mfa, verify_mfa_setup
from .models import User
from .schemas import (
    AdminResetPasswordRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    MfaBackupCodesResponse,
    MfaChallengeResponse,
    MfaLoginRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    RefreshRequest,
    SchoolOptionResponse,
  SelectSchoolRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from .schools import fetch_schools, find_school_name
from .service import AuthService
from .tokens import create_access_token, create_refresh_token, decode_mfa_token, decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenResponse | MfaChallengeResponse)
@rate_limit("5/minute")
async def login(request: Request, body: LoginRequest, session: Session = Depends(get_session)):
    return AuthService(session).login(body, request)


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
):
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            AuthService(session).logout(payload.get("jti", ""))
        except JWTError:
            pass  # Already invalid, still return 200
    return {"ok": True}


@router.post("/refresh", response_model=TokenResponse)
@rate_limit("10/minute")
async def refresh(request: Request, body: RefreshRequest, session: Session = Depends(get_session)):
    # service logs successful refresh; invalid tokens raise
    return AuthService(session).refresh(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser = Depends(get_current_user)):
    return UserResponse(
        id=current_user.user_id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
        must_change_password=current_user.must_change_password,
        mfa_enabled=current_user.mfa_enabled,
        mfa_verified=current_user.mfa_verified,
        identity_provider=current_user.identity_provider,
        school_id=current_user.school_id,
        school_name=current_user.school_name,
    )


@router.get("/schools", response_model=list[SchoolOptionResponse])
async def list_schools():
    """Return Mashov schools as normalized options for registration forms."""
    try:
        schools = await fetch_schools()
        return [SchoolOptionResponse(school_id=s.school_id, school_name=s.school_name) for s in schools]
    except Exception as exc:
        logger.exception("schools_fetch_failed")
        raise HTTPException(status_code=502, detail="Failed to fetch schools list") from exc


@router.get("/my-schools", response_model=list[SchoolOptionResponse])
async def my_schools(
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Return the schools this user can operate in.

    For global admins, this returns an empty list (school selection is optional).
    """
    from .models import UserSchoolMembership

    if current_user.is_global_admin:
        return []

    memberships = session.exec(
        select(UserSchoolMembership).where(UserSchoolMembership.user_id == current_user.user_id)
    ).all()
    memberships.sort(key=lambda m: (m.school_name or "", m.school_id))
    return [
        SchoolOptionResponse(school_id=m.school_id, school_name=m.school_name or str(m.school_id))
        for m in memberships
    ]


@router.post("/select-school", response_model=TokenResponse)
async def select_school(
    body: SelectSchoolRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Switch the active school scope for the current session by issuing new tokens."""
    from .models import UserSchoolMembership, UserSession

    # Validate requested school_id.
    school_id = body.school_id

    if current_user.is_global_admin:
        # Global admins may optionally "view as" any Mashov school.
        schools = await fetch_schools()
        school_name = find_school_name(schools, school_id)
        if school_name is None:
            raise HTTPException(status_code=422, detail="Invalid school_id")
    else:
        # School-scoped roles must be members of the requested school.
        allowed = session.exec(
            select(UserSchoolMembership).where(
                UserSchoolMembership.user_id == current_user.user_id,
                UserSchoolMembership.school_id == school_id,
            )
        ).first()
        if not allowed:
            raise HTTPException(status_code=403, detail="Not allowed for this school")
        school_name = allowed.school_name

    # Revoke old session (by JTI) and mint a new session+tokens.
    old = session.exec(
        select(UserSession).where(
            UserSession.token_jti == current_user.session_jti,
            UserSession.is_revoked == False,  # noqa: E712
        )
    ).first()
    if old:
        old.is_revoked = True
        session.add(old)
        session.commit()

    user = session.get(User, current_user.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token, jti, expires_at = create_access_token(
        user.id,
        user.role.value,
        mfa_verified=current_user.mfa_verified,
        school_id=school_id,
    )
    refresh_token, _ = create_refresh_token(user.id, jti, school_id=school_id)

    new_session = UserSession(
        user_id=user.id,
        token_jti=jti,
        expires_at=expires_at,
        ip_address=old.ip_address if old else None,
        user_agent=old.user_agent if old else None,
        mfa_verified=current_user.mfa_verified,
    )
    session.add(new_session)
    session.commit()
    logger.info(
        "school_selected",
        extra={
            "user_id": str(user.id),
            "role": user.role.value,
            "school_id": school_id,
            "school_name": school_name,
        },
    )
    log_event(
        session,
        action="select_school",
        user_id=user.id,
        user_email=user.email,
        success=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        detail={"school_id": school_id, "school_name": school_name},
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.put("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    AuthService(session).change_password(db_user, body)
    log_event(session, action="password_change", user_id=db_user.id, user_email=db_user.email, success=True)
    return {"ok": True}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    # School admins only see users for their selected school.
    if _admin.role.value == "school_admin" and _admin.school_id is not None:
        return session.exec(select(User).where(User.school_id == _admin.school_id)).all()
    return session.exec(select(User)).all()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    # School admins may only create users within their selected school.
    if _admin.role.value == "school_admin":
        if _admin.school_id is None:
            raise HTTPException(status_code=403, detail="School scope required")
        if body.school_id is None:
            body.school_id = _admin.school_id
        if body.school_id != _admin.school_id:
            raise HTTPException(status_code=403, detail="Not allowed for this school")

    if body.school_id is not None:
        schools = await fetch_schools()
        school_name = find_school_name(schools, body.school_id)
        if school_name is None:
            raise HTTPException(status_code=422, detail="Invalid school_id")
        body.school_name = school_name
    else:
        body.school_name = None
    user = AuthService(session).create_user(body)
    log_event(
        session,
        action="user_create",
        user_id=_admin.user_id,
        user_email=_admin.email,
        success=True,
        detail={"created_user_id": str(user.id), "created_email": user.email, "created_role": user.role.value, "school_id": user.school_id},
    )
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    from uuid import UUID
    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if _admin.role.value == "school_admin":
        if _admin.school_id is None:
            raise HTTPException(status_code=403, detail="School scope required")
        if user.school_id != _admin.school_id:
            raise HTTPException(status_code=403, detail="Not allowed for this school")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        # School admins cannot grant system/super admin.
        if _admin.role.value == "school_admin" and body.role.value in ("super_admin", "system_admin"):
            raise HTTPException(status_code=403, detail="Not allowed to assign this role")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    # school_id: when provided, validate against Mashov schools list and persist derived name.
    # Note: Pydantic distinguishes between omitted vs explicit null via model_fields_set.
    if "school_id" in body.model_fields_set:
        if _admin.role.value == "school_admin":
            # School admins cannot change a user's school.
            if body.school_id is None or body.school_id != _admin.school_id:
                raise HTTPException(status_code=403, detail="Not allowed to change school")
        if body.school_id is None:
            user.school_id = None
            user.school_name = None
        else:
            schools = await fetch_schools()
            school_name = find_school_name(schools, body.school_id)
            if school_name is None:
                raise HTTPException(status_code=422, detail="Invalid school_id")
            user.school_id = body.school_id
            user.school_name = school_name
    session.add(user)
    session.commit()
    session.refresh(user)
    log_event(
        session,
        action="user_update",
        user_id=_admin.user_id,
        user_email=_admin.email,
        success=True,
        detail={"target_user_id": str(user.id), "target_email": user.email, "role": user.role.value, "school_id": user.school_id, "is_active": user.is_active},
    )
    return user


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    from uuid import UUID
    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if _admin.role.value == "school_admin":
        if _admin.school_id is None or user.school_id != _admin.school_id:
            raise HTTPException(status_code=403, detail="Not allowed for this school")
    AuthService(session).admin_reset_password(user, body.new_password, body.must_change_password)
    log_event(
        session,
        action="admin_reset_password",
        user_id=_admin.user_id,
        user_email=_admin.email,
        success=True,
        detail={"target_user_id": str(user.id), "target_email": user.email, "must_change_password": body.must_change_password},
    )
    return {"ok": True}


@router.post("/users/{user_id}/reset-mfa")
async def admin_reset_mfa(
    user_id: str,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    from uuid import UUID

    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if _admin.role.value == "school_admin":
        if _admin.school_id is None or user.school_id != _admin.school_id:
            raise HTTPException(status_code=403, detail="Not allowed for this school")

    # Clear MFA secrets + backup codes
    user.mfa_secret = None
    user.mfa_enabled = False
    user.mfa_backup_codes = None
    session.add(user)

    # Revoke all active sessions to force re-login
    from .models import UserSession

    sessions = session.exec(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.is_revoked == False,  # noqa: E712
        )
    ).all()
    for s in sessions:
        s.is_revoked = True
        session.add(s)

    session.commit()
    log_event(
        session,
        action="admin_reset_mfa",
        user_id=_admin.user_id,
        user_email=_admin.email,
        success=True,
        detail={"target_user_id": str(user.id), "target_email": user.email},
    )
    return {"ok": True}


# MFA endpoints (MoE section 4.2)

@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    """Initiate TOTP setup. Returns secret + provisioning URI for QR code.
    MFA is NOT active until /mfa/verify is called successfully.
    """
    secret, uri = setup_mfa(db_user)
    session.add(db_user)
    session.commit()
    log_event(session, action="mfa_setup_start", user_id=db_user.id, user_email=db_user.email, success=True)
    return MfaSetupResponse(provisioning_uri=uri, secret=secret)


@router.post("/mfa/verify", response_model=MfaBackupCodesResponse)
async def mfa_verify(
    body: MfaVerifyRequest,
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    """Confirm TOTP setup with the first code from the authenticator app.
    Activates MFA and returns one-time backup codes.
    """
    plaintext_codes = verify_mfa_setup(db_user, body.code)
    session.add(db_user)
    session.commit()
    log_event(session, action="mfa_enabled", user_id=db_user.id, user_email=db_user.email, success=True)
    return MfaBackupCodesResponse(backup_codes=plaintext_codes)


@router.post("/mfa/challenge", response_model=TokenResponse)
async def mfa_challenge(
    body: MfaLoginRequest,
    session: Session = Depends(get_session),
):
    """Complete MFA login. Submit the mfa_token from /login plus a TOTP code
    (or backup code) to receive full access + refresh tokens.
    The issued session has mfa_verified=True.
    """
    import logging as _log
    from uuid import UUID

    from jose import JWTError

    from ..audit.service import log_event

    try:
        payload = decode_mfa_token(body.mfa_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="MFA token invalid or expired")

    user = session.get(User, UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    check_mfa_code(user, body.code)
    session.add(user)  # persist any consumed backup code

    from .models import UserSession
    from .tokens import create_access_token, create_refresh_token

    # Issue tokens with mfa_verified=True embedded in the JWT claim and session record
    access_token, jti, expires_at = create_access_token(
        user.id, user.role.value, mfa_verified=True, school_id=user.school_id
    )
    refresh_token, _ = create_refresh_token(user.id, jti, school_id=user.school_id)
    new_session = UserSession(
        user_id=user.id, token_jti=jti, expires_at=expires_at, mfa_verified=True
    )
    session.add(new_session)
    session.commit()
    log_event(session, action="login", user_id=user.id, user_email=user.email, success=True, detail={"mfa": True})
    _log.getLogger(__name__).info("mfa_login_success", extra={"user_id": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/mfa/disable")
async def mfa_disable(
    body: MfaVerifyRequest,
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
    _write: None = Depends(require_write_access),
):
    """Disable MFA. Requires the current TOTP code (or a backup code) to confirm."""
    disable_mfa(db_user, body.code)
    session.add(db_user)
    session.commit()
    log_event(session, action="mfa_disabled", user_id=db_user.id, user_email=db_user.email, success=True)
    return {"ok": True}


# SSO / OpenID Connect endpoints (MoE section 4.1)

@router.get("/sso/login")
async def sso_login(request: Request):
    """Redirect the browser to the configured OIDC provider's authorization endpoint."""
    import secrets as _secrets

    from fastapi.responses import RedirectResponse

    from .sso import get_authorization_url

    state = _secrets.token_urlsafe(16)
    # Store state in a short-lived cookie for CSRF validation in the callback
    auth_url = await get_authorization_url(state)
    response = RedirectResponse(url=auth_url)
    response.set_cookie("sso_state", state, max_age=300, httponly=True, samesite="lax")
    return response


@router.get("/sso/callback")
async def sso_callback(
    code: str,
    state: str,
    request: Request,
    session: Session = Depends(get_session),
):
    """Handle the authorization code callback from the OIDC provider.
    Provisions or finds the local user and issues JWT tokens.
    Redirects to the frontend with the access token in the URL fragment.
    """
    from fastapi.responses import RedirectResponse

    from ..audit.service import log_event
    from .sso import exchange_code_for_user_info, issue_tokens_for_user, provision_sso_user

    # CSRF validation
    stored_state = request.cookies.get("sso_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid SSO state parameter")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    userinfo = await exchange_code_for_user_info(code)
    user = provision_sso_user(session, userinfo)
    tokens = issue_tokens_for_user(session, user, ip, ua)

    log_event(session, action="sso_login", user_id=user.id, user_email=user.email, success=True, ip_address=ip, user_agent=ua)
    logger.info("sso_login_success", extra={"user_id": str(user.id)})

    # Redirect to frontend with tokens in the URL fragment (never in query string)
    from ..constants import ORIGIN_URL
    redirect_url = f"{ORIGIN_URL}/#sso_login={tokens['access_token']}&refresh={tokens['refresh_token']}"
    response = RedirectResponse(url=redirect_url)
    response.delete_cookie("sso_state")
    return response


@router.get("/sso/status")
async def sso_status():
    """Check whether SSO is configured and available."""
    from .sso import is_sso_enabled
    return {"sso_enabled": is_sso_enabled()}
