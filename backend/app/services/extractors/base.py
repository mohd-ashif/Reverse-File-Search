from abc import ABC, abstractmethod
from pathlib import Path


class TextExtractor(ABC):
    """Extracts plain text from a single file for embedding."""

    @abstractmethod
    def extract(self, path: Path) -> str:
        raise NotImplementedError
