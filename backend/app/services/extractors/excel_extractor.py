from pathlib import Path

from app.services.extractors.base import TextExtractor


class ExcelExtractor(TextExtractor):
    """Interface placeholder - Excel extraction is not implemented yet."""

    def extract(self, path: Path) -> str:
        raise NotImplementedError("Excel extraction is not implemented yet")
