from functools import lru_cache

from app.core.config import settings


class EmbeddingService:
    """Lazy-loads the sentence-transformers model on first use."""

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self._model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.model.encode(texts, convert_to_numpy=True).tolist()


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
