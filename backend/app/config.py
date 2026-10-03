"""Central configuration.

Every setting can be overridden through an environment variable or a `.env`
file (see `.env.example`). Defaults are chosen so that the application boots
and is fully usable on a laptop with no external services.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------- general --------------------------------
    app_name: str = "Mahabharata Wisdom AI"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ------------------------------- storage --------------------------------
    storage_backend: str = "local"  # local | postgres
    sqlite_path: str = "./data/mahabharata.db"
    postgres_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/mahabharata"
    vector_dim: int = 512

    # ------------------------------ embeddings ------------------------------
    embedding_provider: str = "local"  # local | openai | gemini

    # --------------------------------- LLM ----------------------------------
    llm_provider: str = "none"  # none | openai | anthropic | gemini
    generator: str = "auto"  # auto | llm | template
    analyst: str = "auto"  # auto | llm | rule
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2600
    http_timeout_seconds: float = 60.0

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-sonnet-4-5"

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"

    # ------------------------------ retrieval -------------------------------
    retrieval_candidates: int = 40
    retrieval_top_k: int = 8
    rerank_top_k: int = 6
    min_semantic_score: float = 0.05
    strong_support_threshold: float = 0.34
    min_relevance_cut: float = 0.06
    require_primary_text_for_strong_support: bool = True

    # --------------------------------- auth ---------------------------------
    auth_required: bool = False
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 10080
    admin_email: str = "admin@example.com"
    admin_password: str = "admin1234"
    admin_name: str = "Corpus Administrator"

    # ------------------------------- daily ----------------------------------
    reflection_seed: str = "mahabharata-wisdom"

    # ------------------------------ validators ------------------------------
    @field_validator("storage_backend")
    @classmethod
    def _check_storage(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"local", "postgres"}:
            raise ValueError("STORAGE_BACKEND must be 'local' or 'postgres'")
        return v

    @field_validator("embedding_provider", "llm_provider")
    @classmethod
    def _check_provider(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def _require_secure_production_settings(self) -> "Settings":
        """Reject convenient local defaults when the app is deployed publicly."""
        if self.environment.lower() != "production":
            return self
        if not self.auth_required:
            raise ValueError("AUTH_REQUIRED must be true in production")
        if self.jwt_secret == "change-me-to-a-long-random-string" or len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be a unique value of at least 32 characters in production")
        if self.admin_password == "admin1234" or len(self.admin_password) < 12:
            raise ValueError("ADMIN_PASSWORD must be a unique value of at least 12 characters in production")
        if not self.cors_origins or "*" in self.origin_list:
            raise ValueError("CORS_ORIGINS must list explicit origins in production")
        return self

    # ------------------------------- derived --------------------------------
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        if self.storage_backend == "postgres":
            return self.postgres_url
        path = Path(self.sqlite_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"

    @property
    def data_dir(self) -> Path:
        d = BASE_DIR / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def vector_store_dir(self) -> Path:
        d = self.data_dir / "store"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def effective_generator(self) -> str:
        if self.generator != "auto":
            return self.generator
        return "llm" if self.llm_provider != "none" and self._has_key() else "template"

    @property
    def effective_analyst(self) -> str:
        if self.analyst != "auto":
            return self.analyst
        return "llm" if self.llm_provider != "none" and self._has_key() else "rule"

    def _has_key(self) -> bool:
        return bool(
            {
                "openai": self.openai_api_key,
                "anthropic": self.anthropic_api_key,
                "gemini": self.gemini_api_key,
            }.get(self.llm_provider))
        # noqa: E501


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
