from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChangeOps"
    database_url: str = "postgresql+psycopg://changeops:changeops@localhost:5432/changeops"
    extraction_model_provider: str = "openai"
    extraction_model: str = "gpt-5.6-luna"
    extraction_model_timeout_seconds: float = 120.0
    extraction_model_max_retries: int = 0
    interpretation_model_provider: str = "openai"
    interpretation_model: str = "gpt-5.6-luna"
    interpretation_model_timeout_seconds: float = 120.0
    interpretation_model_max_retries: int = 0
    openai_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
