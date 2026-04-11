"""
config.py – Centralised application configuration for AI-DAN.

Uses pydantic-settings to load values from environment variables and
.env files.  All external-service credentials are surfaced here so
that integration clients never read os.environ directly.

When ``STRICT_PROD=true`` the system **refuses to start** unless every
secret required for real dispatch → callback → deploy is configured.
This prevents silent fallback paths from masquerading as production.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache as _lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # --- Strict Production Mode ------------------------------------------------
    # When True the system fails fast on startup if any required production
    # secret is missing.  Set STRICT_PROD=true in production environments.
    strict_prod: bool = False

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

    # --- Anthropic (Claude) ----------------------------------------------------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # --- Groq (fast inference) -------------------------------------------------
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Deepseek (code + cost) -----------------------------------------------
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # --- xAI Grok (real-time trends) ------------------------------------------
    grok_api_key: str = ""
    grok_model: str = "grok-3-mini"

    # --- GitHub Integration ----------------------------------------------------
    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_factory_owner: str = "ismaelloveexcel"
    github_factory_template_repo: str = "saas-template"
    # External factory workflow dispatch target.
    factory_owner: str = "ismaelloveexcel"
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
    factory_secret: str = ""
    alert_webhook_url: str = ""

    # --- Portfolio Registry ----------------------------------------------------
    portfolio_db_path: str = _default_portfolio_db_path()

    # --- Turso (libSQL) persistence --------------------------------------------
    turso_database_url: str = ""
    turso_auth_token: str = ""

    # --- API Security ----------------------------------------------------------
    api_key: str = ""

    # --- Memory / Learning -----------------------------------------------------
    memory_max_events: int = 2000

    # --- Notifications (Telegram) ---------------------------------------------
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Payments (LemonSqueezy) ----------------------------------------------
    lemonsqueezy_api_key: str = ""
    lemonsqueezy_store_id: str = ""

    # -- production readiness helpers ------------------------------------------

    def validate_production_secrets(self) -> list[str]:
        """Return a list of missing-but-required secrets for production.

        These are the secrets needed for a real
        dispatch → callback → deploy loop to function without fallbacks.
        """
        missing: list[str] = []
        if not self.github_token:
            missing.append("GITHUB_TOKEN")
        if not self.factory_callback_secret:
            missing.append("FACTORY_CALLBACK_SECRET")
        if not self.public_base_url:
            missing.append("PUBLIC_BASE_URL")
        if not self.vercel_token:
            missing.append("VERCEL_TOKEN")
        return missing


class _StrictProdError(RuntimeError):
    """Raised when STRICT_PROD is enabled and required secrets are missing."""


@_lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached application settings instance.

    When ``STRICT_PROD=true`` and required production secrets are missing,
    raises :class:`_StrictProdError` to prevent the system from starting
    in a broken-but-silent state.
    """
    settings = Settings()

    if settings.strict_prod:
        missing = settings.validate_production_secrets()
        if missing:
            msg = (
                "STRICT_PROD is enabled but the following required secrets "
                f"are missing: {', '.join(missing)}.  Set them in the "
                "environment or disable STRICT_PROD for development."
            )
            raise _StrictProdError(msg)

    return settings
