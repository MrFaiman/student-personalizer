from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    """Immutable audit log for all security-relevant events."""

    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: UUID | None = Field(default=None, index=True)  # None = system/anonymous
    user_email: str | None = None
    action: str = Field(index=True)  # e.g. "login", "upload", "delete_import", "train_model"
    resource: str | None = None  # e.g. "import:batch_id", "student:tz"
    detail: str | None = None  # JSON string with extra context
    success: bool = True
    ip_address: str | None = None
    user_agent: str | None = None
