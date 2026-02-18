"""Abstract base class for all tenant-scoped services."""

from abc import ABC
from uuid import UUID

from sqlmodel import Session


class BaseService(ABC):
    def __init__(self, session: Session, school_id: UUID):
        self.session = session
        self.school_id = school_id
