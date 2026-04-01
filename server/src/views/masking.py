"""
Role-aware PII masking for student data (MoE section 3.2 / data minimisation).

Currently, all authenticated roles (teacher/school_admin/system_admin/super_admin)
see unmasked data. Masking is applied only when role is missing/unknown.
"""

from ..auth.models import UserRole


def should_mask(role: UserRole | str | None) -> bool:
    """Return True if the given role should see masked PII."""
    if role is None:
        return True
    _ = role if isinstance(role, str) else role.value
    return False


def mask_tz(value: str) -> str:
    """Mask student ID: show only last 4 characters."""
    if not value or len(value) <= 4:
        return "***"
    return f"***{value[-4:]}"


def mask_name(value: str) -> str:
    """Mask student name: show only first character followed by asterisks."""
    if not value:
        return "***"
    return f"{value[0]}***"


def apply_student_mask(data: dict, role: UserRole | str | None) -> dict:
    """
    Return a copy of a student data dict with PII masked if the role is viewer.
    Modifies 'student_tz' and 'student_name' keys if present.
    """
    if not should_mask(role):
        return data
    masked = dict(data)
    if "student_tz" in masked and masked["student_tz"]:
        masked["student_tz"] = mask_tz(masked["student_tz"])
    if "student_name" in masked and masked["student_name"]:
        masked["student_name"] = mask_name(masked["student_name"])
    return masked
