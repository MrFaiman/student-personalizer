from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Literal

import httpx

from ..config import settings

Verdict = Literal["clean", "malicious", "unknown", "skipped"]


@dataclass(frozen=True)
class VirusTotalScanResult:
    verdict: Verdict
    analysis_id: str | None = None
    stats: dict[str, int] | None = None
    reason: str | None = None

    @property
    def is_clean(self) -> bool:
        return self.verdict == "clean"

    @property
    def should_block(self) -> bool:
        return self.verdict == "malicious"


VT_FILES_URL = "https://www.virustotal.com/api/v3/files"
VT_UPLOAD_URL = "https://www.virustotal.com/api/v3/files/upload_url"
VT_ANALYSES_URL = "https://www.virustotal.com/api/v3/analyses/{analysis_id}"
VT_DIRECT_UPLOAD_MAX_BYTES = 32 * 1024 * 1024
VT_PUBLIC_API_MAX_PER_MINUTE = 4
VT_PUBLIC_API_MAX_PER_DAY = 500


def _headers(api_key: str) -> dict[str, str]:
    return {"x-apikey": api_key}


def _verdict_from_stats(stats: dict[str, int] | None) -> Verdict:
    if not stats:
        return "unknown"
    malicious = int(stats.get("malicious", 0) or 0)
    suspicious = int(stats.get("suspicious", 0) or 0)
    if malicious > 0 or suspicious > 0:
        return "malicious"
    return "clean"


def _extract_analysis_id(upload_json: dict) -> str | None:
    # Expected: {"data": {"id": "<analysis_id>", ...}}
    data = upload_json.get("data") if isinstance(upload_json, dict) else None
    if not isinstance(data, dict):
        return None
    analysis_id = data.get("id")
    return analysis_id if isinstance(analysis_id, str) and analysis_id else None


def _extract_upload_url(upload_url_json: dict) -> str | None:
    # Expected: {"data": "<url>"}
    data = upload_url_json.get("data") if isinstance(upload_url_json, dict) else None
    return data if isinstance(data, str) and data else None


class _VirusTotalRateLimiter:
    """
    Best-effort local guardrail for VirusTotal Public API limits.

    Notes:
    - Process-local only (won't coordinate across multiple server instances).
    - Conservatively counts each outbound HTTP call (upload + each poll request).
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._minute_window_started_at: float | None = None
        self._minute_count = 0
        self._day: date | None = None
        self._day_count = 0

    async def try_acquire(self) -> bool:
        async with self._lock:
            now = asyncio.get_event_loop().time()

            if self._minute_window_started_at is None or (now - self._minute_window_started_at) >= 60.0:
                self._minute_window_started_at = now
                self._minute_count = 0

            today = date.today()
            if self._day is None or self._day != today:
                self._day = today
                self._day_count = 0

            if self._minute_count >= VT_PUBLIC_API_MAX_PER_MINUTE:
                return False
            if self._day_count >= VT_PUBLIC_API_MAX_PER_DAY:
                return False

            self._minute_count += 1
            self._day_count += 1
            return True


_rate_limiter = _VirusTotalRateLimiter()


def _extract_status_and_stats(analysis_json: dict) -> tuple[str | None, dict[str, int] | None]:
    # Expected: {"data": {"attributes": {"status": "...", "stats": {...}}}}
    data = analysis_json.get("data") if isinstance(analysis_json, dict) else None
    if not isinstance(data, dict):
        return None, None
    attrs = data.get("attributes")
    if not isinstance(attrs, dict):
        return None, None
    status = attrs.get("status")
    raw_stats = attrs.get("stats")
    if isinstance(raw_stats, dict):
        stats: dict[str, int] = {}
        for k, v in raw_stats.items():
            if isinstance(k, str):
                try:
                    stats[k] = int(v)
                except Exception:
                    continue
        return status if isinstance(status, str) else None, stats
    return status if isinstance(status, str) else None, None


async def scan_file(
    file_content: bytes,
    *,
    filename: str,
    password: str | None = None,
    timeout_seconds: float | None = None,
    poll_interval_seconds: float | None = None,
    max_wait_seconds: float | None = None,
    api_key: str | None = None,
) -> VirusTotalScanResult:
    """
    Submit a file to VirusTotal and wait for analysis completion (best-effort within max_wait_seconds).
    Returns verdict=unknown if the analysis doesn't complete in time.
    """
    key = (api_key or settings.virustotal_api_key or "").strip()
    if not key:
        return VirusTotalScanResult(verdict="skipped", reason="api_key_not_configured")

    timeout = timeout_seconds if timeout_seconds is not None else settings.virustotal_timeout_seconds
    poll_every = poll_interval_seconds if poll_interval_seconds is not None else settings.virustotal_poll_interval_seconds
    max_wait = max_wait_seconds if max_wait_seconds is not None else settings.virustotal_max_wait_seconds

    async with httpx.AsyncClient(timeout=timeout) as client:
        data: dict[str, str] | None = {"password": password} if password else None
        files = {"file": (filename, file_content)}
        if not await _rate_limiter.try_acquire():
            return VirusTotalScanResult(verdict="skipped", reason="rate_limited")
        if len(file_content) > VT_DIRECT_UPLOAD_MAX_BYTES:
            if not await _rate_limiter.try_acquire():
                return VirusTotalScanResult(verdict="skipped", reason="rate_limited")
            u = await client.get(VT_UPLOAD_URL, headers=_headers(key))
            u.raise_for_status()
            upload_url = _extract_upload_url(u.json())
            if not upload_url:
                return VirusTotalScanResult(verdict="unknown", reason="missing_upload_url")
            resp = await client.post(upload_url, headers=_headers(key), files=files, data=data)
        else:
            resp = await client.post(VT_FILES_URL, headers=_headers(key), files=files, data=data)
        resp.raise_for_status()
        upload_json = resp.json()

        analysis_id = _extract_analysis_id(upload_json)
        if not analysis_id:
            return VirusTotalScanResult(verdict="unknown", reason="missing_analysis_id")

        deadline = asyncio.get_event_loop().time() + float(max_wait)
        while True:
            if not await _rate_limiter.try_acquire():
                return VirusTotalScanResult(verdict="skipped", analysis_id=analysis_id, stats=None, reason="rate_limited")
            a = await client.get(VT_ANALYSES_URL.format(analysis_id=analysis_id), headers=_headers(key))
            a.raise_for_status()
            analysis_json = a.json()
            status, stats = _extract_status_and_stats(analysis_json)
            if status == "completed":
                verdict = _verdict_from_stats(stats)
                return VirusTotalScanResult(verdict=verdict, analysis_id=analysis_id, stats=stats)

            now = asyncio.get_event_loop().time()
            if now >= deadline:
                return VirusTotalScanResult(verdict="unknown", analysis_id=analysis_id, stats=stats, reason="analysis_timeout")

            await asyncio.sleep(float(poll_every))

