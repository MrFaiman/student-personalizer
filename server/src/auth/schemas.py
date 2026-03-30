from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from .models import UserRole
from .password import PASSWORD_MIN_LENGTH


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
        return v


class CreateUserRequest(BaseModel):
    email: str
    display_name: str
    password: str
    role: UserRole = UserRole.viewer
    must_change_password: bool = True


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    must_change_password: bool

    model_config = {"from_attributes": True}


class AdminResetPasswordRequest(BaseModel):
    new_password: str
    must_change_password: bool = True
