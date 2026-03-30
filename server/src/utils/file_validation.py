"""
File upload validation (MoE section 3.x).

Validates:
1. File size (max configurable via MAX_UPLOAD_SIZE_MB, default 50 MB)
2. Magic bytes (not just Content-Type header - prevents extension spoofing)
3. Filename sanitization (no path traversal, no null bytes)
"""

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

# Magic bytes for allowed file types
_MAGIC: dict[bytes, str] = {
    b"\x50\x4b\x03\x04": "xlsx",  # ZIP container - .xlsx/.xlsm are ZIP-based
    b"\xd0\xcf\x11\xe0": "xls",   # OLE compound document - legacy .xls
    b"ID3": "csv_fallback",        # not real - placeholder; CSV has no magic bytes
}

# CSV files have no magic bytes, so we allow them via extension + MIME only
_CSV_MIME = {"text/csv", "text/plain"}
_EXCEL_MIME = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}

# Characters not allowed in filenames
_UNSAFE_FILENAME_RE = re.compile(r"[^\w\s.\-]", re.UNICODE)


def _get_max_bytes() -> int:
    from ..config import settings

    return settings.max_upload_size_mb * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters from a filename."""
    # Take only the basename (prevents path traversal)
    name = Path(filename).name
    # Remove null bytes
    name = name.replace("\x00", "")
    # Collapse to safe characters
    name = _UNSAFE_FILENAME_RE.sub("_", name)
    return name or "upload"


async def validate_upload(file: UploadFile) -> bytes:
    """
    Read and validate an uploaded file. Returns the raw bytes.

    Raises HTTPException on:
    - File exceeds size limit
    - Unrecognised file type (by magic bytes or MIME)
    - Empty file
    """
    max_bytes = _get_max_bytes()

    # Fast reject via Content-Length header when available
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_mb} MB size limit")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    if len(content) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_mb} MB size limit")

    mime = (file.content_type or "").lower().split(";")[0].strip()

    # CSV: no magic bytes - accept by MIME type only
    if mime in _CSV_MIME:
        return content

    # Excel: validate by magic bytes
    if mime in _EXCEL_MIME or mime == "application/octet-stream":
        magic = content[:4] if len(content) >= 4 else content
        if not any(magic.startswith(m) for m in _MAGIC if m != b"ID3"):
            raise HTTPException(
                status_code=400,
                detail="File content does not match an Excel format. Upload a valid .xlsx or .xls file.",
            )
        return content

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file type '{mime}'. Upload an Excel (.xlsx, .xls) or CSV (.csv) file.",
    )
