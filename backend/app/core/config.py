"""
Central application configuration loaded from environment variables.
Never import secrets directly — always use this settings object.
"""
from functools import lru_cache
from typing import List, Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "WalchandGPT"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Server ─────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Database ───────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://walchand:walchand_secret@localhost:5432/walchandgpt"
    SYNC_DATABASE_URL: str = "postgresql://walchand:walchand_secret@localhost:5432/walchandgpt"

    # ── JWT ────────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── LLM ────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["openai", "google", "ollama", "openai_compatible"] = "openai"
    MODEL_NAME: str = "gpt-4o-mini"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    GOOGLE_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # ── Embeddings ─────────────────────────────────────────────
    EMBEDDING_PROVIDER: Literal["openai", "google", "ollama", "huggingface"] = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # ── MCP Server ─────────────────────────────────────────────
    MCP_SERVER_HOST: str = "0.0.0.0"
    MCP_SERVER_PORT: int = 8001
    MCP_SERVER_URL: str = "http://localhost:8001"

    # ── Redis ──────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Storage ────────────────────────────────────────────────
    STORAGE_PROVIDER: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./storage/uploads"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "walchandgpt-documents"

    # ── CORS ───────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Rate Limiting ──────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── RAG ────────────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
    MAX_CONTEXT_TOKENS: int = 4000

    # ── Observability ──────────────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "walchandgpt"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
