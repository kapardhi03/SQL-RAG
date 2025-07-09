from typing import Optional

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    POSTGRES_DSN: PostgresDsn = "postgres://postgres:root@localhost:5432/postgres"

    OPENAI_API_KEY: Optional[str] = None

    ANTHROPIC_API_KEY: Optional[str] = None

    GOOGLE_API_KEY: Optional[str] = None

    AZURE_GPT_ENDPOINT: Optional[str] = None
    AZURE_GPT_KEY: Optional[str] = None


settings = Settings()
