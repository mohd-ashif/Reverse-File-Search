from pathlib import Path

from app.models.file import FileType

_EXTENSION_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".txt": FileType.TXT,
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
    ".png": FileType.IMAGE,
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".bmp": FileType.IMAGE,
    ".tiff": FileType.IMAGE,
    ".tif": FileType.IMAGE,
    ".xlsx": FileType.EXCEL,
    ".xls": FileType.EXCEL,
}

SUPPORTED_EXTENSIONS = frozenset(_EXTENSION_MAP.keys())


def detect_file_type(path: str | Path) -> FileType:
    extension = Path(path).suffix.lower()
    return _EXTENSION_MAP.get(extension, FileType.UNKNOWN)


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS
