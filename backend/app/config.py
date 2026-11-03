"""Configuration management using Pydantic Settings."""

from functools import lru_cache
import logging
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

INSECURE_DEFAULT_KEYS = {
    "dev-admin-key",
    "secret",
    "admin",
    "change-me",
    "password",
    "12345678",
    "dev-session-secret-key-do-not-use-in-production-32b",
}


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

    # Database & Redis Persistence
    DATABASE_URL: Optional[str] = Field(default=None, description="SQLAlchemy database connection string (PostgreSQL or SQLite)")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis connection URL for distributed rate limiting and state coordination")

    # Security & Admin Access
    ADMIN_API_KEY: str = Field(default="dev-admin-key", description="Secret token for document ingestion and admin APIs")
    SECRET_KEY: str = Field(default="dev-session-secret-key-do-not-use-in-production-32b", description="Secret key for signing short-lived session tokens")
    SESSION_TOKEN_EXPIRE_SECONDS: int = Field(default=3600, description="Session token TTL in seconds (1 hour)")
    KILL_SWITCH_ENABLED: bool = Field(default=False, description="Emergency stop switch for all AI operations")
    DISCORD_WEBHOOK_URL: str = Field(default="", description="Optional Discord webhook URL for human escalation alerts")

    # Rate Limiting & Usage Limits
    RATE_LIMIT_PER_MINUTE: int = Field(default=30, description="Max requests per client IP per minute")
    MAX_UPLOAD_SIZE_MB: int = Field(default=15, description="Max allowed file upload size in MB")
    MAX_RETRIEVAL_CHUNKS: int = Field(default=5, description="Top-K chunks sent to context window")
    SIMILARITY_SCORE_THRESHOLD: float = Field(default=0.35, description="Minimum cosine similarity threshold")
    MAX_QUESTION_LENGTH: int = Field(default=500, description="Max character length for user questions")
    WS_MAX_CONNECTIONS_PER_SESSION: int = Field(default=5, description="Max simultaneous WebSocket connections for a single session")
    WS_MAX_MESSAGES_PER_MINUTE: int = Field(default=20, description="Max messages per minute per WebSocket connection")

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

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Strict fail-fast validation for production deployments."""
        is_prod = self.ENVIRONMENT.lower() == "production"

        if is_prod:
            # 1. Require strong, non-default ADMIN_API_KEY
            if not self.ADMIN_API_KEY or self.ADMIN_API_KEY in INSECURE_DEFAULT_KEYS:
                raise ValueError(
                    "CRITICAL SECURITY FAILURE: ADMIN_API_KEY cannot be empty or a default insecure key in production! "
                    "Set a secure, random environment variable ADMIN_API_KEY (minimum 32 characters)."
                )
            if len(self.ADMIN_API_KEY) < 32:
                raise ValueError("CRITICAL SECURITY FAILURE: ADMIN_API_KEY must be at least 32 characters long in production.")

            # 2. Require strong, non-default SECRET_KEY
            if not self.SECRET_KEY or self.SECRET_KEY in INSECURE_DEFAULT_KEYS:
                raise ValueError(
                    "CRITICAL SECURITY FAILURE: SECRET_KEY cannot be empty or a default insecure key in production! "
                    "Set a secure, random environment variable SECRET_KEY (minimum 32 characters)."
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError("CRITICAL SECURITY FAILURE: SECRET_KEY must be at least 32 characters long in production.")

            # 3. Require OPENAI_API_KEY
            if not self.OPENAI_API_KEY:
                raise ValueError("CRITICAL SECURITY FAILURE: OPENAI_API_KEY must be set in production.")

            # 4. Require DEBUG=False
            if self.DEBUG:
                raise ValueError("CRITICAL SECURITY FAILURE: DEBUG mode must be disabled (DEBUG=False) in production.")

        return self

    def __repr__(self) -> str:
        """Never expose secrets in string representations or logs."""
        return (
            f"Settings(ENVIRONMENT='{self.ENVIRONMENT}', DEBUG={self.DEBUG}, "
            f"APP_HOST='{self.APP_HOST}', APP_PORT={self.APP_PORT}, "
            f"ADMIN_API_KEY='***', SECRET_KEY='***', OPENAI_API_KEY='***')"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
