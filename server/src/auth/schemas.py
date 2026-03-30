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


class MfaChallengeResponse(BaseModel):
    """Returned by /login when the user has MFA enabled.
    The client must POST this mfa_token + TOTP code to /mfa/challenge.
    """
    mfa_required: bool = True
    mfa_token: str


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
    mfa_enabled: bool = False

    model_config = {"from_attributes": True}


class AdminResetPasswordRequest(BaseModel):
    new_password: str
    must_change_password: bool = True


# MFA schemas (MoE section 4.2)
class MfaSetupResponse(BaseModel):
    """Returned when MFA setup is initiated — contains provisioning URI for QR code."""
    provisioning_uri: str
    secret: str  # base32 secret shown to user for manual entry


class MfaVerifyRequest(BaseModel):
    """TOTP code to verify during setup or login."""
    code: str


class MfaBackupCodesResponse(BaseModel):
    """Plaintext backup codes shown once after MFA activation."""
    backup_codes: list[str]


class MfaLoginRequest(BaseModel):
    """Second-factor submission during login when MFA is enabled."""
    mfa_token: str  # JWT from first-factor login, used to identify pending session
    code: str       # 6-digit TOTP code or backup code
