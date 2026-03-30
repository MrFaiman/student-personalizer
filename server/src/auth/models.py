from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, Enum):
    admin = "admin"
    teacher = "teacher"
    viewer = "viewer"


class User(SQLModel, table=True):
    """System user with role-based access."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    hashed_password: str
    role: UserRole = Field(default=UserRole.viewer)
    is_active: bool = Field(default=True)
    must_change_password: bool = Field(default=False)
    failed_login_attempts: int = Field(default=0)
    locked_until: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    sessions: list["UserSession"] = Relationship(back_populates="user")
    password_history: list["PasswordHistory"] = Relationship(back_populates="user")


class UserSession(SQLModel, table=True):
    """Active user session tracking."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    token_jti: str = Field(index=True, unique=True)  # JWT ID for revocation
    expires_at: datetime
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    ip_address: str | None = None
    user_agent: str | None = None
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional[User] = Relationship(back_populates="sessions")


class PasswordHistory(SQLModel, table=True):
    """Password history to prevent reuse (last 5)."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional[User] = Relationship(back_populates="password_history")
