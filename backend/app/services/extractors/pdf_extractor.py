from pathlib import Path

import fitz  # PyMuPDF

from app.services.extractors.base import TextExtractor


class PdfExtractor(TextExtractor):
    def extract(self, path: Path) -> str:
        text_parts: list[str] = []
        with fitz.open(path) as document:
            for page in document:
                text_parts.append(page.get_text())
        return "\n".join(text_parts).strip()
