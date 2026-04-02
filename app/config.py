

# app/config.py

from functools import lru_cache
from typing import Optional

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # API KEY (x-api-key)
    # =========================
    # Utilisée pour protéger /contacts, /emails/*, /settings/*
    API_KEY: str = Field(default="dev-ibcb-secret-key")

    # =========================
    # Base de données principale (ex. PostgreSQL)
    # =========================
    DATABASE_URL: AnyUrl

    # =========================
    # Redis (pour RQ, cache, etc.)
    # =========================
    REDIS_URL: AnyUrl = "redis://redis:6379/0"

    # =========================
    # SMTP (Gmail / Google Workspace / autre serveur SMTP)
    # =========================
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SENDER_NAME: str = "iBCB Email System"

    # =========================
    # SendGrid
    # =========================
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: Optional[str] = None

    # =========================
    # Mailgun
    # =========================
    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_DOMAIN: Optional[str] = None

    # =========================
    # Auth backend (admin)
    # =========================
    ADMIN_EMAIL: str = "contact@ibcb-a.com"
    #ADMIN_PASSWORD: str =
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",          # refuse les variables inattendues (sécurité)
        case_sensitive=False,    # API_KEY, api_key, Api_Key -> ok
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique de Settings (singleton via lru_cache)."""
    return Settings()
