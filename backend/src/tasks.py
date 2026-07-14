import os
from pathlib import Path
from uuid import UUID

from celery import Celery
from celery.exceptions import Ignore

from src.db import SyncSessionLocal
from src.enums import AlertLevel, ProcessingStatus, ScanStatus
from src.models import Alert, StoredFile
from src.service import STORAGE_DIR

REDIS_URL = os.environ.get("REDIS_URL", "redis://backend-redis:6379/0")
celery_app = Celery("file_tasks", broker=REDIS_URL, backend=REDIS_URL)


@celery_app.task
def scan_file_for_threats(file_id: UUID) -> UUID:
    with SyncSessionLocal.begin() as session:
        file_item = session.get(StoredFile, file_id)
        if not file_item:
            raise Ignore

        file_item.processing_status = ProcessingStatus.PROCESSING
        reasons: list[str] = []
        extension = Path(file_item.original_name).suffix.lower()

        if extension in {".exe", ".bat", ".cmd", ".sh", ".js"}:
            reasons.append(f"suspicious extension {extension}")

        if file_item.size > 10 * 1024 * 1024:
            reasons.append("file is larger than 10 MB")

        if extension == ".pdf" and file_item.mime_type not in {"application/pdf", "application/octet-stream"}:
            reasons.append("pdf extension does not match mime type")

        file_item.scan_status = ScanStatus.SUSPICIOUS if reasons else ScanStatus.CLEAN
        file_item.scan_details = ", ".join(reasons) if reasons else "no threats found"
        file_item.requires_attention = bool(reasons)

    extract_file_metadata.delay(file_id)
    return file_id


@celery_app.task
def extract_file_metadata(file_id: UUID) -> UUID:
    with SyncSessionLocal.begin() as session:
        file_item = session.get(StoredFile, file_id)
        if not file_item:
            raise Ignore

        stored_path = STORAGE_DIR / file_item.stored_name
        if not stored_path.exists():
            file_item.processing_status = ProcessingStatus.FAILED
            file_item.scan_status = file_item.scan_status or ScanStatus.FAILED
            file_item.scan_details = "stored file not found during metadata extraction"
            return file_id

        metadata = {
            "extension": Path(file_item.original_name).suffix.lower(),
            "size_bytes": file_item.size,
            "mime_type": file_item.mime_type,
        }

        if file_item.mime_type.startswith("text/"):
            content = stored_path.read_text(encoding="utf-8", errors="ignore")
            metadata["line_count"] = len(content.splitlines())
            metadata["char_count"] = len(content)
        elif file_item.mime_type == "application/pdf":
            content = stored_path.read_bytes()
            metadata["approx_page_count"] = max(content.count(b"/Type /Page"), 1)

        file_item.metadata_json = metadata
        file_item.processing_status = ProcessingStatus.PROCESSED
        return file_id


@celery_app.task
def send_file_alert(file_id: UUID) -> None:
    with SyncSessionLocal.begin() as session:
        file_item = session.get(StoredFile, file_id)
        if not file_item:
            return

        if file_item.processing_status == ProcessingStatus.FAILED:
            alert = Alert(file_id=file_id, level=AlertLevel.CRITICAL, message="File processing failed")
        elif file_item.requires_attention:
            alert = Alert(
                file_id=file_id,
                level=AlertLevel.WARNING,
                message=f"File requires attention: {file_item.scan_details}",
            )
        else:
            alert = Alert(file_id=file_id, level=AlertLevel.INFO, message="File processed successfully")

        session.add(alert)
