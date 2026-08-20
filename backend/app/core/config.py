import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


class Settings:
    app_name = "Cost-Aware Knowledge Engine"
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite:///./cost_aware_knowledge_engine.db"
    )
    embedding_provider = os.getenv(
        "EMBEDDING_PROVIDER",
        "deterministic"
    )
    embedding_model = os.getenv(
        "EMBEDDING_MODEL",
        "deterministic-hash-v1"
    )
    embedding_dimensions = int(
        os.getenv("EMBEDDING_DIMENSIONS", "384")
    )
    enable_pgvector = os.getenv(
        "ENABLE_PGVECTOR",
        "false"
    ).lower() == "true"

    # LLM / OpenRouter settings
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model = os.getenv(
        "OPENROUTER_MODEL",
        "openai/gpt-4o-mini"
    )

    # Cache settings
    cache_ttl_seconds = int(
        os.getenv("CACHE_TTL_SECONDS", "300")
    )
    cache_max_entries = int(
        os.getenv("CACHE_MAX_ENTRIES", "1000")
    )

    # Cost tracking
    retrieval_cost_per_query = float(
        os.getenv("RETRIEVAL_COST_PER_QUERY", "0.0001")
    )


settings = Settings()
