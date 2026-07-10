
from enum import StrEnum


class ProcessingStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ScanStatus(StrEnum):
    SUSPICIOUS = "suspicious"
    CLEAN = "clean"
    FAILED = "failed"


class AlertLevel(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"