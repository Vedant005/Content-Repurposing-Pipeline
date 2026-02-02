from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str
    DATABASE_URL: str
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()