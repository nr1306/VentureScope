from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it works regardless of cwd
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # OpenAI — all LLM calls
    openai_api_key: str = ""
    openai_agent_model: str = "gpt-4o-mini"       # specialist agents (tool-use loop)
    openai_synthesis_model: str = "gpt-4o-mini"   # final report synthesis + LLM judge
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Web search
    tavily_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://venturesscope:venturesscope@localhost:5432/venturesscope"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 8
    max_upload_bytes: int = 50 * 1024 * 1024  # 50MB
    max_chunks_per_doc: int = 5000

    # Agent
    max_agent_iterations: int = 10
    confidence_threshold: float = 0.4


settings = Settings()
