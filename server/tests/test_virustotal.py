import types

import pytest

from src.config import settings
from src.integrations.virustotal import scan_file


class _FakeResponse:
    def __init__(self, json_data: dict, *, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._json_data


class _FakeAsyncClient:
    def __init__(self, *, timeout: float):
        self.timeout = timeout
        self.calls: list[tuple[str, str]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, *, headers: dict, files: dict, data: dict | None = None):
        self.calls.append(("POST", url))
        return _FakeResponse({"data": {"id": "analysis_123"}})

    async def get(self, url: str, *, headers: dict):
        self.calls.append(("GET", url))
        return _FakeResponse({"data": {"attributes": {"status": "completed", "stats": {"malicious": 1, "suspicious": 0}}}})


@pytest.mark.anyio
async def test_scan_skipped_when_no_api_key(monkeypatch):
    old = settings.virustotal_api_key
    settings.virustotal_api_key = ""
    try:
        result = await scan_file(b"abc", filename="x.csv")
        assert result.verdict == "skipped"
        assert result.reason == "api_key_not_configured"
    finally:
        settings.virustotal_api_key = old


@pytest.mark.anyio
async def test_scan_marks_malicious(monkeypatch):
    old = settings.virustotal_api_key
    settings.virustotal_api_key = "test-key"
    try:
        import src.integrations.virustotal as vt

        monkeypatch.setattr(vt, "httpx", types.SimpleNamespace(AsyncClient=_FakeAsyncClient))

        result = await scan_file(b"abc", filename="x.xlsx", max_wait_seconds=5, poll_interval_seconds=0)
        assert result.verdict == "malicious"
        assert result.analysis_id == "analysis_123"
        assert result.stats and result.stats.get("malicious") == 1
    finally:
        settings.virustotal_api_key = old


@pytest.mark.anyio
async def test_scan_timeout_returns_unknown(monkeypatch):
    class _TimeoutClient(_FakeAsyncClient):
        async def get(self, url: str, *, headers: dict):
            self.calls.append(("GET", url))
            return _FakeResponse({"data": {"attributes": {"status": "queued", "stats": {"malicious": 0, "suspicious": 0}}}})

    old = settings.virustotal_api_key
    settings.virustotal_api_key = "test-key"
    try:
        import src.integrations.virustotal as vt

        monkeypatch.setattr(vt, "httpx", types.SimpleNamespace(AsyncClient=_TimeoutClient))

        result = await scan_file(b"abc", filename="x.xlsx", max_wait_seconds=0, poll_interval_seconds=0)
        assert result.verdict == "unknown"
        assert result.reason == "analysis_timeout"
        assert result.analysis_id == "analysis_123"
    finally:
        settings.virustotal_api_key = old


@pytest.mark.anyio
async def test_large_file_uses_upload_url(monkeypatch):
    class _LargeFileClient(_FakeAsyncClient):
        async def get(self, url: str, *, headers: dict):
            self.calls.append(("GET", url))
            if url.endswith("/files/upload_url"):
                return _FakeResponse({"data": "https://upload.example.test/vt"})
            return await super().get(url, headers=headers)

    old = settings.virustotal_api_key
    settings.virustotal_api_key = "test-key"
    try:
        import src.integrations.virustotal as vt

        monkeypatch.setattr(vt, "httpx", types.SimpleNamespace(AsyncClient=_LargeFileClient))
        monkeypatch.setattr(vt, "_rate_limiter", vt._VirusTotalRateLimiter())

        big = b"a" * (vt.VT_DIRECT_UPLOAD_MAX_BYTES + 1)
        result = await scan_file(big, filename="big.xlsx", max_wait_seconds=5, poll_interval_seconds=0)
        assert result.verdict == "malicious"
    finally:
        settings.virustotal_api_key = old

