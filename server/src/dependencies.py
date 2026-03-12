from fastapi import HTTPException

_preview_mode = False


def get_preview_mode() -> bool:
    return _preview_mode


def set_preview_mode(value: bool):
    global _preview_mode
    _preview_mode = value


def require_write_access():
    """Block ALL data mutations when preview mode is active. No exceptions."""
    if _preview_mode:
        raise HTTPException(status_code=403, detail="Preview mode is active. Data modifications are disabled.")
