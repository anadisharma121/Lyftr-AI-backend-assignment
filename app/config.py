from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    WEBHOOK_SECRET: str
    DATABASE_URL: str = "sqlite:////data/app.db"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()