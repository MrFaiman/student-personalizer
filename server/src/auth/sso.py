"""SSO / OpenID Connect integration (MoE section 4.1).

Supports any standard OIDC provider (Microsoft Entra ID, Google Workspace,
or the Israeli MoE identity provider).

Configuration (env vars):
  OIDC_CLIENT_ID        - OAuth2 client ID (required to enable SSO)
  OIDC_CLIENT_SECRET    - OAuth2 client secret
  OIDC_DISCOVERY_URL    - Provider discovery URL ending in /.well-known/openid-configuration
                          e.g. https://login.microsoftonline.com/<tenant>/v2.0
  OIDC_REDIRECT_URI     - Must match the redirect URI registered with the provider
                          e.g. https://students.school.il/api/auth/sso/callback

Flow:
  1. GET  /api/auth/sso/login     → redirect to provider's authorization endpoint
  2. GET  /api/auth/sso/callback  → exchange code for tokens, provision/find user, issue JWT
"""

import logging
import os
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from ..auth.models import User, UserRole, UserSession
from ..auth.password import hash_password
from ..auth.tokens import create_access_token, create_refresh_token
from ..utils.clock import utc_now

logger = logging.getLogger(__name__)

OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL", "")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "")
OIDC_SCOPE = os.getenv("OIDC_SCOPE", "openid email profile")

# Cached provider metadata (fetched once on first use)
_provider_metadata: dict | None = None


def is_sso_enabled() -> bool:
    return bool(OIDC_CLIENT_ID and OIDC_CLIENT_SECRET and OIDC_DISCOVERY_URL)


async def _get_provider_metadata() -> dict:
    global _provider_metadata
    if _provider_metadata is not None:
        return _provider_metadata
    async with httpx.AsyncClient() as client:
        url = OIDC_DISCOVERY_URL.rstrip("/") + "/.well-known/openid-configuration"
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _provider_metadata = resp.json()
    return _provider_metadata


async def get_authorization_url(state: str) -> str:
    """Build the provider's authorization URL to redirect the browser to."""
    if not is_sso_enabled():
        raise HTTPException(status_code=501, detail="SSO is not configured")
    meta = await _get_provider_metadata()
    params = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": OIDC_SCOPE,
        "redirect_uri": OIDC_REDIRECT_URI,
        "state": state,
    }
    return f"{meta['authorization_endpoint']}?{urlencode(params)}"


async def exchange_code_for_user_info(code: str) -> dict:
    """Exchange authorization code for user info from the OIDC provider."""
    meta = await _get_provider_metadata()
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            meta["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": OIDC_REDIRECT_URI,
                "client_id": OIDC_CLIENT_ID,
                "client_secret": OIDC_CLIENT_SECRET,
            },
            timeout=10,
        )
        if token_resp.status_code != 200:
            logger.warning("sso_token_exchange_failed", extra={"status": token_resp.status_code})
            raise HTTPException(status_code=401, detail="SSO token exchange failed")
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            meta["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to fetch user info from provider")
        return userinfo_resp.json()


def provision_sso_user(session: Session, userinfo: dict) -> User:
    """Find or create a local user from OIDC userinfo claims.

    New SSO users are created as 'teacher' role by default. An admin can
    upgrade the role manually.

    Account-linking rules (prevent takeover via unverified email assertions):
    1. Provider MUST assert ``email_verified=true``.
    2. If a local account already exists:
       a. If it was provisioned via OIDC (``identity_provider != "local"``),
          allow login and keep ``external_subject_id`` in sync.
       b. If it is a local-password account, refuse automatic linking.
          An admin must explicitly convert the account to OIDC first.
    3. Otherwise, provision a new OIDC-only account.
    """
    # Require verified email from the provider
    if not userinfo.get("email_verified", False):
        raise HTTPException(
            status_code=403,
            detail="OIDC provider did not verify the user's email address",
        )

    email = (userinfo.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="OIDC provider did not return an email claim")

    user = session.exec(select(User).where(User.email == email)).first()
    external_subject = userinfo.get("sub", "")

    if user:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")

        # Block auto-linking to a local-only account - prevents account takeover
        if user.identity_provider == "local" and user.external_subject_id is None:
            logger.warning(
                "sso_link_blocked_local_account",
                extra={"email": email, "reason": "local account exists without prior OIDC binding"},
            )
            raise HTTPException(
                status_code=409,
                detail="A local account with this email already exists. "
                       "Ask an administrator to link the account to SSO.",
            )

        # Keep external_subject_id in sync on subsequent OIDC logins
        if external_subject and user.external_subject_id != external_subject:
            user.external_subject_id = external_subject
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    # Provision new user - no password (SSO-only account)
    display_name = userinfo.get("name") or userinfo.get("given_name") or email.split("@")[0]
    user = User(
        email=email,
        display_name=display_name,
        hashed_password=hash_password(f"sso-{email}-no-password-{utc_now().isoformat()}"),
        role=UserRole.teacher,
        must_change_password=False,
        identity_provider="oidc",
        external_subject_id=external_subject or None,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info("sso_user_provisioned", extra={"email": email})
    return user


def issue_tokens_for_user(session: Session, user: User, ip: str | None, ua: str | None) -> dict:
    """Create session and return access + refresh tokens for an SSO-authenticated user."""
    access_token, jti, expires_at = create_access_token(
        user.id, user.role.value, mfa_verified=False, school_id=user.school_id
    )
    refresh_token, _ = create_refresh_token(user.id, jti, school_id=user.school_id)
    new_session = UserSession(
        user_id=user.id,
        token_jti=jti,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=ua,
    )
    session.add(new_session)
    session.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
