"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment: development, test, production")
    DEBUG: bool = Field(default=False, description="Enable debug mode (disable in production)")
    APP_HOST: str = Field(default="127.0.0.1", description="Host address for binding")
    APP_PORT: int = Field(default=8000, description="Port for binding")

    # OpenAI API Configuration
    OPENAI_API_KEY: str = Field(default="", description="Secret OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="Configurable OpenAI Chat Model")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Configurable Embedding Model")
    OPENAI_BASE_URL: Union[str, None] = Field(default=None, description="Optional custom base URL for OpenAI-compatible providers like Gemini, Groq, OpenRouter, or Ollama")

    # Storage Paths (resolved to absolute paths relative to project root)
    DATA_DIR: Path = Field(default=PROJECT_ROOT / "data", description="Base data directory")
    INDEX_DIR: Path = Field(default=PROJECT_ROOT / "data" / "index", description="FAISS index and metadata directory")
    DOCS_DIR: Path = Field(default=PROJECT_ROOT / "data" / "docs", description="PDF files storage directory")

    # Security & Admin Access
    ADMIN_API_KEY: str = Field(default="dev-admin-key", description="Secret token for document ingestion and management")
    KILL_SWITCH_ENABLED: bool = Field(default=False, description="Emergency stop switch for new LLM requests")

    # Rate Limiting & Usage Limits
    RATE_LIMIT_PER_MINUTE: int = Field(default=30, description="Max requests per client IP per minute")
    MAX_UPLOAD_SIZE_MB: int = Field(default=15, description="Max allowed file upload size in MB")
    MAX_RETRIEVAL_CHUNKS: int = Field(default=5, description="Top-K chunks sent to context window")
    SIMILARITY_SCORE_THRESHOLD: float = Field(default=0.35, description="Minimum cosine similarity threshold")
    MAX_QUESTION_LENGTH: int = Field(default=500, description="Max character length for user questions")

    # Allowed Origins for CORS (string or list)
    ALLOWED_ORIGINS: Union[List[str], str] = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        description="Comma-separated or JSON list of CORS origins"
    )

    @property
    def cors_origins(self) -> List[str]:
        """Return parsed list of CORS origins."""
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        return ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
