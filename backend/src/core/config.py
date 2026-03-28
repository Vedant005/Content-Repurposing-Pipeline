from typing import List, Union

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str
    DATABASE_URL: str
    GROQ_API_KEY: str
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]
    ENV: str = "prod"

    class Config:
        env_file = ".env"

settings = Settings()
