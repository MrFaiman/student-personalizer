"""
SQLAlchemy TypeDecorator for transparent AES-256-GCM encryption of TEXT columns.

Usage in a SQLModel:
    from src.crypto.encrypted_type import EncryptedString

    class MyModel(SQLModel, table=True):
        secret: str = Field(sa_column=Column(EncryptedString))
"""

from sqlalchemy import String, TypeDecorator

from .field_encryption import decrypt, encrypt


class EncryptedString(TypeDecorator):
    """Stores an encrypted string in a TEXT column."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        """Encrypt before writing to DB."""
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        """Decrypt after reading from DB."""
        if value is None:
            return None
        return decrypt(value)
