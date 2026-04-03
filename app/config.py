

# app/config.py

import os
from functools import lru_cache
from typing import Optional

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_KEY: str = Field(default="dev-ibcb-secret-key")

    DATABASE_URL: AnyUrl
    REDIS_URL: AnyUrl = "redis://redis:6379/0"

    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SENDER_NAME: str = "iBCB Email System"

    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: Optional[str] = None

    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_DOMAIN: Optional[str] = None

    ADMIN_EMAIL: str = "contact@ibcb-a.com"
    ADMIN_PASSWORD: Optional[str] = os.getenv("ADMIN_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


