from dataclasses import dataclass
from datetime import timedelta

import httpx

from ..utils.clock import utc_now

SCHOOLS_API_URL = "https://web.mashov.info/api/schools"
SCHOOLS_CACHE_TTL = timedelta(hours=6)


@dataclass(frozen=True)
class SchoolOption:
    school_id: int
    school_name: str


_schools_cache: list[SchoolOption] | None = None
_schools_cache_at = None


def _normalize_schools(payload: list[dict]) -> list[SchoolOption]:
    options: list[SchoolOption] = []
    for item in payload:
        semel = item.get("semel")
        name = item.get("name")
        if isinstance(semel, int) and isinstance(name, str) and name.strip():
            options.append(SchoolOption(school_id=semel, school_name=name.strip()))
    options.sort(key=lambda s: s.school_name)
    return options


async def fetch_schools(force_refresh: bool = False) -> list[SchoolOption]:
    global _schools_cache, _schools_cache_at

    if not force_refresh and _schools_cache is not None and _schools_cache_at is not None:
        if utc_now() - _schools_cache_at < SCHOOLS_CACHE_TTL:
            return _schools_cache

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(SCHOOLS_API_URL)
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, list):
        raise ValueError("Invalid schools API response shape")

    schools = _normalize_schools(data)
    _schools_cache = schools
    _schools_cache_at = utc_now()
    return schools


def find_school_name(schools: list[SchoolOption], school_id: int) -> str | None:
    for school in schools:
        if school.school_id == school_id:
            return school.school_name
    return None
