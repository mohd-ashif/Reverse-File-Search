from pathlib import Path

from app.services.extractors.base import TextExtractor


class TxtExtractor(TextExtractor):
    def extract(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace").strip()
