import re
from pathlib import Path

import markdown

from app.services.extractors.base import TextExtractor

_TAG_RE = re.compile(r"<[^>]+>")


class MarkdownExtractor(TextExtractor):
    def extract(self, path: Path) -> str:
        raw = path.read_text(encoding="utf-8", errors="replace")
        html = markdown.markdown(raw)
        return _TAG_RE.sub(" ", html).strip()
