

# app/config.py

from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de données principale (ex. PostgreSQL)
    DATABASE_URL: AnyUrl

    # Redis (pour RQ, cache, etc.)
    REDIS_URL: AnyUrl = "redis://redis:6379/0"

    # SMTP (Gmail / Google Workspace / autre serveur SMTP)
    SMTP_SERVER: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SENDER_NAME: str = "iBCB Email System"

    # SendGrid
    SENDGRID_API_KEY: str | None = None
    SENDGRID_FROM_EMAIL: str | None = None

    # Mailgun
    MAILGUN_API_KEY: str | None = None
    MAILGUN_DOMAIN: str | None = None

    # -------------------------
    # Auth backend (admin)
    # -------------------------
    # Ces valeurs doivent être surchargées par le fichier .env
    ADMIN_EMAIL: str = "contact@ibcb-a.com"
    ADMIN_PASSWORD: str = "demo123!!@@"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """
    Retourne une instance unique de Settings (pattern singleton via lru_cache).
    """
    return Settings()


