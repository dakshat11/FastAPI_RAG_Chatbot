# core/config.py
# pydantic-settings reads your .env file and maps each variable to a typed
# Python field. If a required field is missing, the app crashes at startup
# with a clear error — better to fail fast at startup than silently at runtime.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required — must exist in .env, no default value
    openai_api_key: str

    # Optional — have defaults, can be overridden in .env
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    sqlite_db_path: str = "chatbot.db"
    alpha_vantage_api_key: str = "C9PE94QUEW9VWGFM"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retriever_k: int = 4
    tts_voice: str = "alloy"  # for Phase 6: alloy, echo, fable, onyx, nova, shimmer

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Module-level singleton.
# Importing this triggers the .env read ONCE.
# Every other module does: from core.config import settings
settings = Settings()