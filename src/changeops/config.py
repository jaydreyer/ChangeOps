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
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None
    jira_project_id_or_key: str | None = None
    jira_issue_type_id: str | None = None
    jira_timeout_seconds: float = 10.0
    confluence_base_url: str | None = None
    confluence_email: str | None = None
    confluence_api_token: SecretStr | None = None
    confluence_timeout_seconds: float = 10.0
    confluence_manager_travel_approval_guide_page_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
