import logging
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from kombu.exceptions import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db import SessionLocal
from src.schemas import AlertItem, FileItem, FileUpdate
from src.service import STORAGE_DIR, create_file, delete_file, get_file, list_alerts, list_files, update_file
from src.tasks import scan_file_for_threats

logger = logging.getLogger(__name__)


app = FastAPI()
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


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session  # noqa: ASYNC119


DbSession = Annotated[AsyncSession, Depends(get_session)]


@app.get("/files", response_model=list[FileItem])
async def list_files_view(db: DbSession):
    return await list_files(db)


@app.get("/alerts", response_model=list[AlertItem])
async def list_alerts_view(db: DbSession):
    return await list_alerts(db)


@app.post("/files", response_model=FileItem, status_code=status.HTTP_201_CREATED)
async def create_file_view(
    title: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    db: DbSession,
):
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
):
    return await update_file(db, file_id=file_id, title=payload.title)


@app.get("/files/{file_id}/download")
async def download_file(file_id: UUID, db: DbSession):
    file_item = await get_file(db, file_id)
    stored_path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
    return FileResponse(
        path=stored_path,
        media_type=file_item.mime_type,
        filename=file_item.original_name,
    )


@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_view(file_id: UUID, db: DbSession):
    await delete_file(db, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
