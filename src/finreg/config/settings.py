"""Typed application configuration settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="finreg-intelligence", description="Application name")
    environment: str = Field(default="development", description="Execution environment")
    log_level: str = Field(default="INFO", description="Logging verbosity level")
    host: str = Field(default="0.0.0.0", description="API host address")
    port: int = Field(default=8000, description="API port number")

    # PostgreSQL Database
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="finreg_db", description="PostgreSQL database name")
    postgres_user: str = Field(default="finreg_user", description="PostgreSQL username")
    postgres_password: str = Field(default="finreg_password", description="PostgreSQL password")

    # Vector Database Settings (Anticipated for Future Phases)
    vector_table: str = Field(default="chunk_embeddings", description="Vector database table name")
    vector_dimension: int = Field(default=1536, description="Embedding vector dimension")
    vector_distance_metric: str = Field(default="cosine", description="Vector distance metric")

    # LLM Provider Settings (Anticipated for Future Phases)
    llm_provider: str = Field(default="openai", description="LLM provider name")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model identifier")
    llm_api_key: str | None = Field(default=None, description="LLM provider API key")
    llm_base_url: str | None = Field(default=None, description="LLM provider base URL endpoint")

    # Embedding Provider Settings (Anticipated for Future Phases)
    embedding_provider: str = Field(default="openai", description="Embedding provider name")
    embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model identifier"
    )
    embedding_api_key: str | None = Field(default=None, description="Embedding API key")
    embedding_dimension: int = Field(default=1536, description="Target embedding dimension")

    @property
    def database_url(self) -> str:
        """Construct standard SQLAlchemy PostgreSQL connection URL."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of Application Settings."""
    return Settings()
