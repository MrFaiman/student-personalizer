from sqlmodel import Session, select

from .models import Permission, RolePermission, UserRoleLink


def assert_school_scope(*, school_id: int | None) -> int:
    if school_id is None:
        raise PermissionError("School scope required")
    return school_id


def assert_permission(
    session: Session,
    *,
    user_id,
    school_id: int | None,
    permission_key: str,
) -> None:
    """Service-layer authorization check (defense-in-depth).

    Routers should enforce permissions via dependencies; this is an additional guard
    for high-risk service methods so they remain safe if reused elsewhere.
    """
    # Global roles always apply; school-scoped roles apply only to the active school_id.
    role_ids_stmt = select(UserRoleLink.role_id).where(UserRoleLink.user_id == user_id)
    if school_id is None:
        role_ids_stmt = role_ids_stmt.where(UserRoleLink.school_id.is_(None))
    else:
        role_ids_stmt = role_ids_stmt.where(
            (UserRoleLink.school_id.is_(None)) | (UserRoleLink.school_id == school_id)
        )

    role_ids = list(session.exec(role_ids_stmt).all())
    if not role_ids:
        raise PermissionError("Insufficient permissions")

    perm_stmt = (
        select(Permission.key)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_(role_ids), Permission.key == permission_key)
    )
    allowed = session.exec(perm_stmt).first()
    if not allowed:
        raise PermissionError("Insufficient permissions")

