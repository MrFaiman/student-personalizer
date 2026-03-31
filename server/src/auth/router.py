import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session, select

from ..database import get_session
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
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from .schools import fetch_schools, find_school_name
from .service import AuthService
from .tokens import decode_mfa_token, decode_token

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


@router.put("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    AuthService(session).change_password(db_user, body)
    return {"ok": True}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    return session.exec(select(User)).all()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    if body.school_id is not None:
        schools = await fetch_schools()
        school_name = find_school_name(schools, body.school_id)
        if school_name is None:
            raise HTTPException(status_code=422, detail="Invalid school_id")
        body.school_name = school_name
    else:
        body.school_name = None
    return AuthService(session).create_user(body)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from uuid import UUID
    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    body: AdminResetPasswordRequest,
    _admin: CurrentUser = Depends(require_admin),
    session: Session = Depends(get_session),
):
    from uuid import UUID
    user = session.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    AuthService(session).admin_reset_password(user, body.new_password, body.must_change_password)
    return {"ok": True}


# ---------------------------------------------------------------------------
# MFA endpoints (MoE section 4.2)
# ---------------------------------------------------------------------------

@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    """Initiate TOTP setup. Returns secret + provisioning URI for QR code.
    MFA is NOT active until /mfa/verify is called successfully.
    """
    secret, uri = setup_mfa(db_user)
    session.add(db_user)
    session.commit()
    return MfaSetupResponse(provisioning_uri=uri, secret=secret)


@router.post("/mfa/verify", response_model=MfaBackupCodesResponse)
async def mfa_verify(
    body: MfaVerifyRequest,
    db_user: User = Depends(get_db_user),
    session: Session = Depends(get_session),
):
    """Confirm TOTP setup with the first code from the authenticator app.
    Activates MFA and returns one-time backup codes.
    """
    plaintext_codes = verify_mfa_setup(db_user, body.code)
    session.add(db_user)
    session.commit()
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
    refresh_token, _ = create_refresh_token(user.id, jti)
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
):
    """Disable MFA. Requires the current TOTP code (or a backup code) to confirm."""
    disable_mfa(db_user, body.code)
    session.add(db_user)
    session.commit()
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
