from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-key"
    DATABASE_URL: str = "postgresql+asyncpg://dev_user:dev_password@localhost:5434/fastapi_template_dev"
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    CORS_ORIGINS: str = "*"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }

@lru_cache
def get_settings():
    return Settings()
