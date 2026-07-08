from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_name: str
    mime_type: str
    size: int
    processing_status: str
    scan_status: str | None
    scan_details: str | None
    metadata_json: dict[str, Any] | None
    requires_attention: bool
    created_at: datetime
    updated_at: datetime


class FileUpdate(BaseModel):
    title: str


class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: UUID
    level: str
    message: str
    created_at: datetime
