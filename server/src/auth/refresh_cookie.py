"""httpOnly refresh token cookie (MoE / browser security hardening)."""

from fastapi.responses import JSONResponse, Response

from ..config import settings


def refresh_cookie_max_age_seconds() -> int:
    return int(settings.refresh_token_expire_hours * 3600)


def attach_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=refresh_cookie_max_age_seconds(),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.refresh_cookie_path,
        domain=settings.cookie_domain or None,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        domain=settings.cookie_domain or None,
    )


def access_token_json_response(access_token: str) -> JSONResponse:
    return JSONResponse({"access_token": access_token, "token_type": "bearer"})
