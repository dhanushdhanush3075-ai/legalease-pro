from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-2.5-flash-lite"

    JWT_SECRET: str = "change-me-in-production-this-is-not-secure"
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30
    OTP_TTL_SECONDS: int = 300
    OTP_DEV_MODE: bool = True

    INDIAN_KANOON_API_TOKEN: str = ""

    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    CORS_ORIGINS: str = "*"
    DATABASE_URL: str = "sqlite:///./legalease.db"
    RATE_LIMIT_PER_MIN: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
