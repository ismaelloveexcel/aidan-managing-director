"""
config.py – Centralised application configuration for AI-DAN.

Uses pydantic-settings to load values from environment variables and
.env files.  All external-service credentials are surfaced here so
that integration clients never read os.environ directly.
"""

import os
from functools import lru_cache as _lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_portfolio_db_path() -> str:
    """Return a writable default database path.

    Vercel's filesystem is read-only outside ``/tmp``, so when the
    ``VERCEL`` environment variable is set we store the SQLite file
    there instead of the local ``data/`` directory.
    """
    if os.environ.get("VERCEL"):
        return "/tmp/portfolio.sqlite3"
    return "data/portfolio.sqlite3"


class Settings(BaseSettings):
    """Application-wide configuration loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application -----------------------------------------------------------
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "info"

    # --- LLM Provider ----------------------------------------------------------
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_base_url: str | None = None

    # --- OpenAI ----------------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # --- Perplexity (Research) -------------------------------------------------
    perplexity_api_key: str = ""
    perplexity_model: str = "sonar"

    # --- GitHub Integration ----------------------------------------------------
    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_factory_owner: str = "ai-dan"
    github_factory_template_repo: str = "saas-template"
    # External factory workflow dispatch target.
    factory_owner: str = "ai-dan"
    factory_repo: str = "ai-dan-factory"
    factory_workflow_id: str = "factory-build.yml"

    # --- Service Registry ------------------------------------------------------
    registry_url: str = "https://registry.example.com"
    registry_api_key: str = ""

    # --- Factory / Deployment --------------------------------------------------
    vercel_token: str = ""
    vercel_team_id: str = ""
    factory_ref: str = "main"
    public_base_url: str = ""
    factory_callback_secret: str = ""

    # --- Portfolio Registry ----------------------------------------------------
    portfolio_db_path: str = _default_portfolio_db_path()

    # --- Turso (libSQL) persistence --------------------------------------------
    turso_database_url: str = ""
    turso_auth_token: str = ""

    # --- API Security ----------------------------------------------------------
    api_key: str = ""

    # --- Memory / Learning -----------------------------------------------------
    memory_max_events: int = 2000


@_lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()
