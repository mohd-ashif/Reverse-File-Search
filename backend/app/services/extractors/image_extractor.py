from pathlib import Path

import pytesseract
from PIL import Image

from app.core.config import settings
from app.services.extractors.base import TextExtractor

if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class ImageOcrExtractor(TextExtractor):
    def extract(self, path: Path) -> str:
        with Image.open(path) as image:
            return pytesseract.image_to_string(image).strip()
