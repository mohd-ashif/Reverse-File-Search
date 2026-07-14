from app.models.file import FileType
from app.services.extractors.base import TextExtractor
from app.services.extractors.docx_extractor import DocxExtractor
from app.services.extractors.excel_extractor import ExcelExtractor
from app.services.extractors.image_extractor import ImageOcrExtractor
from app.services.extractors.markdown_extractor import MarkdownExtractor
from app.services.extractors.pdf_extractor import PdfExtractor
from app.services.extractors.txt_extractor import TxtExtractor

_EXTRACTORS: dict[FileType, TextExtractor] = {
    FileType.PDF: PdfExtractor(),
    FileType.DOCX: DocxExtractor(),
    FileType.TXT: TxtExtractor(),
    FileType.MARKDOWN: MarkdownExtractor(),
    FileType.IMAGE: ImageOcrExtractor(),
    FileType.EXCEL: ExcelExtractor(),
}


def get_extractor(file_type: FileType) -> TextExtractor:
    extractor = _EXTRACTORS.get(file_type)
    if extractor is None:
        raise ValueError(f"No extractor registered for file type: {file_type}")
    return extractor


__all__ = ["TextExtractor", "get_extractor"]
