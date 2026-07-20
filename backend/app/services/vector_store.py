from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class ChromaVectorStore:
    """Wraps a persistent ChromaDB collection used to store chunk embeddings."""

    def __init__(self, persist_dir: str = settings.CHROMA_PERSIST_DIR, collection_name: str = settings.CHROMA_COLLECTION_NAME):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client = None
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=self._persist_dir)
            # Explicit cosine space: embeddings aren't normalized, and Chroma's
            # default (L2/squared-euclidean) distance is unbounded for them, which
            # makes the `1 - distance` similarity score used for confidence go
            # deeply negative on irrelevant chunks. Cosine distance stays in a
            # sane, bounded range regardless of vector norm.
            self._collection = self._client.get_or_create_collection(
                self._collection_name, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        self.collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self.collection.delete(ids=ids)

    def query(self, query_embedding: list[float], top_k: int = 10, where: dict | None = None) -> dict:
        return self.collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)

    def get_by_ids(self, ids: list[str]) -> dict:
        if not ids:
            return {"ids": [], "documents": []}
        return self.collection.get(ids=ids)


@lru_cache
def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore()
