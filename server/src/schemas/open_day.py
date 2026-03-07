from datetime import datetime

from pydantic import BaseModel


class OpenDayRegistrationItem(BaseModel):
    id: int
    import_id: int | None
    submitted_at: datetime | None
    first_name: str
    last_name: str
    student_id: str | None
    parent_name: str | None
    phone: str | None
    email: str | None
    current_school: str | None
    next_grade: str | None
    interested_track: str | None
    referral_source: str | None
    additional_notes: str | None
    import_date: datetime


class OpenDayRegistrationListResponse(BaseModel):
    items: list[OpenDayRegistrationItem]
    total: int
    page: int
    page_size: int


class OpenDayImportItem(BaseModel):
    id: int
    batch_id: str
    filename: str
    rows_imported: int
    rows_failed: int
    import_date: datetime


class OpenDayImportListResponse(BaseModel):
    items: list[OpenDayImportItem]
    total: int


class OpenDayUploadResponse(BaseModel):
    batch_id: str
    rows_imported: int
    rows_failed: int
    errors: list[str]


class OpenDayStats(BaseModel):
    total: int
    by_track: dict[str, int]
    by_grade: dict[str, int]
    by_referral: dict[str, int]
    by_school: dict[str, int]
    by_date: dict[str, int]
    track_by_grade: dict[str, dict[str, int]]
