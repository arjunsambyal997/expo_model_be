from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./summit.db"
    secret_key: str = "dev-only-secret-change-me-in-production-0123456789"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    reset_token_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
    seed_demo_data: bool = True
    # Dev only: no email service yet, so verify/reset tokens are returned in the API response.
    expose_dev_tokens: bool = True


settings = Settings()
