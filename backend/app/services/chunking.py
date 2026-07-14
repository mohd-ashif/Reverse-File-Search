from app.core.config import settings


def chunk_text(
    text: str,
    chunk_size_words: int = settings.CHUNK_SIZE_WORDS,
    overlap_words: int = settings.CHUNK_OVERLAP_WORDS,
) -> list[str]:
    words = text.split()
    if not words:
        return []

    if chunk_size_words <= overlap_words:
        raise ValueError("chunk_size_words must be greater than overlap_words")

    step = chunk_size_words - overlap_words
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size_words]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + chunk_size_words >= len(words):
            break
    return chunks
