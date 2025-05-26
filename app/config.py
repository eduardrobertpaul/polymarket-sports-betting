from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    odds_api_key: str
    prop_odds_api_key: str
    database_url: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of the Settings object.

    Using lru_cache ensures that the settings are only loaded once and then
    cached for future access, improving performance.
    """
    return Settings()
