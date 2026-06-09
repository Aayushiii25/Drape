"""
core/config.py
--------------
Centralised application settings loaded from environment variables.

Design decisions:
    1. Pydantic `BaseSettings` reads from .env automatically — no manual
       os.getenv() scattered across the codebase.
    2. Every setting has a sensible default so the app starts without a
       .env file during development (except WhatsApp secrets, which have
       no safe default and will raise on missing).
    3. Single `settings` instance at module level — import it anywhere:
           from core.config import settings
    4. Kept flat — no nested models.  For an MVP with <15 settings,
       nesting adds indirection without value.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "Drape"
    debug: bool = False

    # ── WhatsApp Cloud API ───────────────────────────────────────────
    # These MUST be set in .env for the webhook to work.
    whatsapp_token: str = ""          # Permanent / temporary access token
    whatsapp_verify_token: str = ""   # Your chosen webhook verify string
    whatsapp_phone_number_id: str = ""  # The phone-number ID from Meta dashboard

    # ── Savana ───────────────────────────────────────────────────────
    savana_base_url: str = "https://api-shop-in.savana.com"
    savana_timeout: float = 10.0
    savana_max_retries: int = 3

    # ── Server ───────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,       # WHATSAPP_TOKEN == whatsapp_token
    )


# Singleton — import this everywhere
settings = Settings()
