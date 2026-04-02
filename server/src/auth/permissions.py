from enum import StrEnum


class PermissionKey(StrEnum):
    # Students
    students_read = "students:read"
    students_write = "students:write"

    # Ingestion / uploads
    ingestion_upload = "ingestion:upload"
    ingestion_logs_read = "ingestion:logs:read"
    ingestion_delete = "ingestion:delete"

    # Analytics / ML
    analytics_read = "analytics:read"
    ml_train = "ml:train"

    # Admin / user management
    admin_users_read = "admin:users:read"
    admin_users_write = "admin:users:write"

    # Config
    config_read = "config:read"
    config_write = "config:write"


ALL_PERMISSION_KEYS: frozenset[str] = frozenset(p.value for p in PermissionKey)

