"""
Validated application settings via Pydantic BaseSettings.
Fails fast at startup if required security env vars are missing.
"""

import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/student_personalizer"
    db_ssl_required: bool = False

    # Server
    port: int = 3000
    origin_url: str = "http://localhost:5173"
    enable_debug: bool = False

    # Auth (MoE 4.1)
    jwt_secret_key: str = ""
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_hours: int = 8
    inactivity_timeout_minutes: int = 30
    auth_required: bool = True

    # Encryption (MoE 3.2, AES-256 for PII at rest)
    # base64-encoded 32-byte key; optional in dev, required when FIELD_ENCRYPTION_REQUIRED=true
    field_encryption_key: str = ""
    field_encryption_required: bool = False

    # HMAC pepper for student_tz search hashes (separate from encryption key)
    hash_pepper: str = ""

    # Uploads
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def validate_security(self) -> None:
        """Call during server startup to enforce required security settings."""
        if self.field_encryption_required and not self.field_encryption_key:
            raise RuntimeError("FIELD_ENCRYPTION_KEY is required when FIELD_ENCRYPTION_REQUIRED=true")
        if self.auth_required and not self.jwt_secret_key:
            raise RuntimeError("JWT_SECRET_KEY is required when AUTH_REQUIRED=true")
        if self.field_encryption_required and not self.hash_pepper:
            raise RuntimeError("HASH_PEPPER is required when FIELD_ENCRYPTION_REQUIRED=true")


settings = Settings(_env_file=os.path.join(os.path.dirname(__file__), "..", ".env"))
