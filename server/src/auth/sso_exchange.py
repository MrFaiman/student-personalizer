"""One-time SSO exchange codes (avoid putting refresh tokens in URL fragments)."""

from __future__ import annotations

import secrets
import threading
import time

_lock = threading.Lock()
# code -> (access_token, refresh_token, monotonic_deadline)
_store: dict[str, tuple[str, str, float]] = {}
TTL_SECONDS = 120.0


def _purge_expired_locked() -> None:
    now = time.monotonic()
    dead = [k for k, (_, _, exp) in _store.items() if exp < now]
    for k in dead:
        del _store[k]


def store_sso_tokens(*, access_token: str, refresh_token: str) -> str:
    """Store tokens; return one-time code for the frontend to redeem."""
    code = secrets.token_urlsafe(32)
    deadline = time.monotonic() + TTL_SECONDS
    with _lock:
        _purge_expired_locked()
        _store[code] = (access_token, refresh_token, deadline)
    return code


def take_sso_tokens(code: str) -> tuple[str, str] | None:
    """Consume code; return (access, refresh) if valid."""
    with _lock:
        _purge_expired_locked()
        entry = _store.pop(code.strip(), None)
    if not entry:
        return None
    access_token, refresh_token, deadline = entry
    if time.monotonic() > deadline:
        return None
    return access_token, refresh_token
