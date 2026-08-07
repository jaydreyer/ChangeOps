from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    app_name: str = "ChangeOps"
    database_url: str | None = "postgresql+psycopg://changeops:changeops@localhost:5432/changeops"
    db_host: str | None = None
    db_port: int = 5432
    db_name: str | None = None
    db_username: str | None = None
    db_password: SecretStr | None = None
    db_sslmode: str = "prefer"
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

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        component_values = (self.db_host, self.db_name, self.db_username, self.db_password)
        if not any(value is not None for value in component_values):
            if not self.database_url:
                raise ValueError("DATABASE_URL or the separate DB_* settings are required.")
            return self
        if not all(value is not None for value in component_values):
            raise ValueError("DB_HOST, DB_NAME, DB_USERNAME, and DB_PASSWORD must be set together.")
        if self.db_sslmode != "require":
            raise ValueError("Component-based database configuration requires DB_SSLMODE=require.")
        self.database_url = URL.create(
            "postgresql+psycopg",
            username=self.db_username,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": "require"},
        ).render_as_string(hide_password=False)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
