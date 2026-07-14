from pydantic import BaseModel


class ScanResult(BaseModel):
    folder_id: int
    added: int = 0
    modified: int = 0
    deleted: int = 0
    skipped: int = 0
    skipped_sensitive: int = 0


class IndexResult(BaseModel):
    extracted: int = 0
    embedded: int = 0
    failed: int = 0


class FolderEstimate(BaseModel):
    path: str
    estimated_files: int
    estimated_supported_files: int
    unsupported_files: int
    approx_scan_seconds: float
    estimated_storage_bytes: int
    large_files_detected: int
    large_file_threshold_bytes: int
    sensitive_files_detected: int
    sensitive_file_samples: list[str]
