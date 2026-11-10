import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Content Repurposing Studio"
    DATABASE_URL: str
    GROQ_API_KEY: str
    SUPADATA_API_KEY: str
    ALLOWED_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "https://content-times.vercel.app",
    ]
    ENV: str = "prod"

    # Redis & Queue settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Groq Model assignments (openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.6-27b)
    GROQ_DEEP_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FAST_MODEL: str = "openai/gpt-oss-20b"
    GROQ_FALLBACK_MODEL: str = "qwen/qwen3.6-27b"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
