from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "Reverse File Search"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/reverse_file_search"

    STORAGE_DIR: str = "./storage"
    CHROMA_PERSIST_DIR: str = "./storage/chroma"
    CHROMA_COLLECTION_NAME: str = "file_chunks"

    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE_WORDS: int = 500
    CHUNK_OVERLAP_WORDS: int = 50

    TESSERACT_CMD: str | None = None

    GROQ_API_KEY: str | None = None
    GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TIMEOUT_SECONDS: float = 20.0

    SCAN_IGNORE_DIR_NAMES: list[str] = [
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        ".idea",
        ".vscode",
        "System Volume Information",
        "$RECYCLE.BIN",
        ".Trash",
    ]

    LARGE_FILE_THRESHOLD_BYTES: int = 50_000_000
    ESTIMATE_FILES_PER_SECOND: float = 50.0
    ESTIMATE_BYTES_PER_SECOND: float = 2_000_000.0

    SECRET_KEY: str = "change-me-in-env"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
