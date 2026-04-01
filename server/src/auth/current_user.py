"""CurrentUser - the resolved identity claims object.

This is the single object that flows through the entire request after
identity resolution.  Business logic and routers receive this instead of
the raw User ORM model, so they are decoupled from the identity layer.

Token/session -> identity resolution -> CurrentUser -> routers/services
"""

from dataclasses import dataclass
from uuid import UUID

from .models import UserRole


@dataclass(frozen=True)
class CurrentUser:
    """Immutable claims object built from a validated JWT + DB session check.

    Fields
    ------
    user_id         Internal UUID - the primary key in the users table.
    email           Verified email address.
    display_name    Human-readable name.
    role            Coarse-grained role used for RBAC gate checks.
    is_active       False means the account has been disabled.
    must_change_password  Forces the client to show a password-change dialog.
    mfa_enabled     True if the user has TOTP configured.
    mfa_verified    True if MFA was completed in *this* session (not just ever).
    identity_provider  "local" | "oidc" | future providers.
    external_id     The external subject identifier (OIDC `sub` claim, etc.).
                    None for local accounts.
    school_id       Mashov semel of the selected school.
    school_name     Human-readable school name from Mashov.
    session_jti     The JWT ID of the current session; used for revocation checks.
    """

    user_id: UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    mfa_enabled: bool
    mfa_verified: bool
    identity_provider: str
    external_id: str | None
    school_id: int | None
    school_name: str | None
    session_jti: str

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.super_admin

    @property
    def is_system_admin(self) -> bool:
        return self.role == UserRole.system_admin

    @property
    def is_school_admin(self) -> bool:
        return self.role == UserRole.school_admin

    @property
    def is_teacher(self) -> bool:
        return self.role == UserRole.teacher

    @property
    def is_global_admin(self) -> bool:
        """Global admin roles that are not tied to a specific school."""
        return self.role in (UserRole.super_admin, UserRole.system_admin)

    def belongs_to_school(self, school_id: int) -> bool:
        """Return True if this user is operating within the given school scope."""
        if self.is_global_admin:
            return True
        return self.school_id == school_id
