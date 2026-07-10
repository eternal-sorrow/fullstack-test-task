from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, func
from sqlmodel import Field, SQLModel

from src.enums import AlertLevel, ProcessingStatus, ScanStatus


class FileBase(SQLModel):
    title: str = Field(max_length=255)
    original_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=255)
    size: int

    processing_status: ProcessingStatus = ProcessingStatus.UPLOADED
    scan_status: ScanStatus | None = None
    scan_details: str | None = Field(default=None, max_length=500)

    metadata_json: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    requires_attention: bool = False


class StoredFile(FileBase, table=True):
    __tablename__: ClassVar[str] = "files"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    stored_name: str = Field(max_length=255, unique=True)

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


class AlertBase(SQLModel):
    level: AlertLevel
    message: str = Field(max_length=500)


class Alert(AlertBase, table=True):
    __tablename__: ClassVar[str] = "alerts"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: int | None = Field(default=None, primary_key=True)
    file_id: UUID = Field(foreign_key="files.id")

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
