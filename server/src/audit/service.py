import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session

from .models import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    session: Session,
    action: str,
    *,
    user_id: UUID | None = None,
    user_email: str | None = None,
    resource: str | None = None,
    detail: dict[str, Any] | None = None,
    success: bool = True,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an immutable audit log entry. Never raises, failures are logged."""
    try:
        entry = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource=resource,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(entry)
        session.commit()
    except Exception as exc:
        logger.error("audit_log_write_failed", exc_info=exc, extra={"action": action})
