from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from ..utils.clock import utc_now


class UserRole(str, Enum):
    super_admin = "super_admin"
    system_admin = "system_admin"
    school_admin = "school_admin"
    teacher = "teacher"
    read_only = "read_only"


class RoleScope(str, Enum):
    global_ = "global"
    school = "school"


class Role(SQLModel, table=True):
    """Normalized RBAC role (can be global or school-scoped)."""

    __tablename__ = "role"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    scope: RoleScope = Field(default=RoleScope.school)
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    permissions: list["RolePermission"] = Relationship(back_populates="role")
    users: list["UserRoleLink"] = Relationship(back_populates="role")


class Permission(SQLModel, table=True):
    """Permission key used for fine-grained authorization checks."""

    __tablename__ = "permission"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key: str = Field(index=True, unique=True)
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    roles: list["RolePermission"] = Relationship(back_populates="permission")


class UserRoleLink(SQLModel, table=True):
    """Assign a role to a user, optionally scoped to a specific school."""

    __tablename__ = "user_role"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    school_id: int | None = Field(default=None, index=True)  # NULL = global assignment
    created_at: datetime = Field(default_factory=utc_now)

    user: Optional["User"] = Relationship(back_populates="role_links")
    role: Optional[Role] = Relationship(back_populates="users")


class RolePermission(SQLModel, table=True):
    """Assign a permission to a role."""

    __tablename__ = "role_permission"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    permission_id: UUID = Field(foreign_key="permission.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)

    role: Optional[Role] = Relationship(back_populates="permissions")
    permission: Optional[Permission] = Relationship(back_populates="roles")


class User(SQLModel, table=True):
    """System user with role-based access."""

    __tablename__ = "user"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    hashed_password: str
    role: UserRole = Field(default=UserRole.teacher)
    is_active: bool = Field(default=True)
    must_change_password: bool = Field(default=False)
    failed_login_attempts: int = Field(default=0)
    locked_until: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # MFA fields (MoE section 4.2)
    mfa_secret: str | None = Field(default=None)        # TOTP secret (base32); None = MFA not configured
    mfa_enabled: bool = Field(default=False)            # True once user completes TOTP setup
    mfa_backup_codes: str | None = Field(default=None)  # JSON array of hashed backup codes

    # Identity provider fields - supports future external IdP integration
    identity_provider: str = Field(default="local")     # "local" | "oidc" | future providers
    external_subject_id: str | None = Field(default=None)  # OIDC `sub` or other external identifier

    # School selection from Mashov schools API (legacy single-school fields).
    # Multi-school membership is represented in UserSchoolMembership.
    school_id: int | None = Field(default=None, index=True)  # Mashov semel
    school_name: str | None = Field(default=None)

    # Relationships
    sessions: list["UserSession"] = Relationship(back_populates="user")
    password_history: list["PasswordHistory"] = Relationship(back_populates="user")
    memberships: list["UserSchoolMembership"] = Relationship(back_populates="user")
    role_links: list[UserRoleLink] = Relationship(back_populates="user")


class UserSchoolMembership(SQLModel, table=True):
    """User access to one or more schools (Mashov semel)."""

    __tablename__ = "user_school_membership"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    school_id: int = Field(index=True)
    school_name: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)

    user: Optional[User] = Relationship(back_populates="memberships")


class UserSession(SQLModel, table=True):
    """Active user session tracking."""

    __tablename__ = "user_session"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token_jti: str = Field(index=True, unique=True)  # JWT ID for revocation
    expires_at: datetime
    last_activity: datetime = Field(default_factory=utc_now)
    ip_address: str | None = None
    user_agent: str | None = None
    is_revoked: bool = Field(default=False)
    mfa_verified: bool = Field(default=False)  # True if MFA was completed in this session
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    user: Optional[User] = Relationship(back_populates="sessions")


class PasswordHistory(SQLModel, table=True):
    """Password history to prevent reuse (last 5)."""

    __tablename__ = "password_history"

    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=utc_now)

    # Relationships
    user: Optional[User] = Relationship(back_populates="password_history")
