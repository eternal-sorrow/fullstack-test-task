import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from kombu.exceptions import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db import SessionLocal
from src.schemas import AlertItem, FileItem, FileUpdate
from src.service import (
    STORAGE_DIR,
    create_file,
    delete_file,
    get_file,
    get_file_path,
    list_alerts,
    list_files,
    update_file,
)
from src.tasks import scan_file_for_threats

if TYPE_CHECKING:
    from src.models import Alert, StoredFile

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session  # noqa: ASYNC119 - FastAPI dependency


DbSession = Annotated[AsyncSession, Depends(get_session)]


@app.get("/files", response_model=list[FileItem])
async def list_files_view(db: DbSession) -> 'Sequence[StoredFile]':
    return await list_files(db)


@app.get("/alerts", response_model=list[AlertItem])
async def list_alerts_view(db: DbSession) -> 'Sequence[Alert]':
    return await list_alerts(db)


@app.post("/files", response_model=FileItem, status_code=status.HTTP_201_CREATED)
async def create_file_view(
    title: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    db: DbSession,
) -> 'StoredFile':
    file_item = await create_file(db, title=title, upload_file=file)
    try:
        scan_file_for_threats.delay(file_item.id)
    except OperationalError:
        logger.exception(
            "Failed to enqueue virus scan for file %s",
            file_item.id,
        )
    return file_item


@app.get("/files/{file_id}", response_model=FileItem)
async def get_file_view(file_id: UUID, db: DbSession):
    return await get_file(db, file_id)


@app.patch("/files/{file_id}", response_model=FileItem)
async def update_file_view(
    file_id: UUID,
    payload: FileUpdate,
    db: DbSession,
) -> 'StoredFile':
    return await update_file(db, file_id=file_id, title=payload.title)


@app.get("/files/{file_id}/download")
async def download_file(file_id: UUID, db: DbSession) -> FileResponse:
    file_item, stored_path = await get_file_path(db, file_id)
    return FileResponse(
        path=stored_path,
        media_type=file_item.mime_type,
        filename=file_item.original_name,
    )


@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_view(file_id: UUID, db: DbSession) -> Response:
    await delete_file(db, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
