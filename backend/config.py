from pathlib import Path
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it works regardless of cwd
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # OpenAI — all LLM calls
    openai_api_key: str = Field(..., min_length=1)
    openai_agent_model: str = Field(default="gpt-4o-mini", min_length=1)       # specialist agents (tool-use loop)
    openai_synthesis_model: str = Field(default="gpt-4o-mini", min_length=1)   # final report synthesis + LLM judge
    embedding_model: str = Field(default="text-embedding-3-small", min_length=1)
    embedding_dimensions: int = Field(default=1536, ge=1)
    openai_timeout_seconds: float = Field(default=45.0, gt=0, le=300)

    # Web search
    tavily_api_key: str = Field(..., min_length=1)
    tavily_timeout_seconds: float = Field(default=20.0, gt=0, le=120)

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://venturesscope:venturesscope@localhost:5432/venturesscope",
        min_length=1,
    )
    db_connect_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    db_statement_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    db_retry_attempts: int = Field(default=3, ge=1, le=5)
    db_retry_backoff_seconds: float = Field(default=1.0, gt=0, le=10)

    # Redis / Celery
    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = Field(default="https://cloud.langfuse.com", min_length=1)

    # RAG
    chunk_size: int = Field(default=1000, ge=200, le=4000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    retrieval_top_k: int = Field(default=8, ge=1, le=20)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)  # 50MB
    max_chunks_per_doc: int = Field(default=5000, ge=1, le=20000)

    # Agent
    max_agent_iterations: int = Field(default=10, ge=1, le=25)
    agent_max_total_tokens: int = Field(default=20000, ge=1024, le=200000)
    confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)

    @field_validator("openai_api_key", "tavily_api_key")
    @classmethod
    def validate_required_api_key(cls, value: str) -> str:
        normalized = value.strip()
        lowered = normalized.lower()
        if not normalized:
            raise ValueError("must be set")
        if lowered.startswith("your_") or lowered.startswith("sk-your"):
            raise ValueError("must be replaced with a real credential")
        return normalized

    @model_validator(mode="after")
    def validate_related_settings(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


settings = Settings()
