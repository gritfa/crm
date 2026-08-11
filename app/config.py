from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "CRM 系统"
    SECRET_KEY: str = "dev-only-change-me"
    DATABASE_URL: str = "sqlite:///./data/crm_system.db"
    SESSION_HTTPS_ONLY: bool = False
    SEED_ADMIN: bool = True
    ADMIN_NAME: str = "系统管理员"
    ADMIN_PHONE: str = "13800000000"
    ADMIN_PASSWORD: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
