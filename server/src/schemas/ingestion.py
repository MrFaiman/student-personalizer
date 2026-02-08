"""Ingestion-related schemas."""

from pydantic import BaseModel


class ImportResponse(BaseModel):
    """Response model for import operations."""

    batch_id: str
    file_type: str
    rows_imported: int
    rows_failed: int
    students_created: int
    classes_created: int
    errors: list[str]


class ImportLogResponse(BaseModel):
    """Response model for import log entries."""

    id: int
    batch_id: str
    filename: str
    file_type: str
    rows_imported: int
    rows_failed: int
    period: str | None
    created_at: str
