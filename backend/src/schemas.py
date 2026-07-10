from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models import AlertBase, FileBase


class FileItem(FileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class FileUpdate(BaseModel):
    title: str


class AlertItem(AlertBase):
    id: int
    file_id: UUID
    created_at: datetime
