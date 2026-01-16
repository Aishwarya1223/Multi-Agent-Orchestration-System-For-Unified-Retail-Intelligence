from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

from dotenv import load_dotenv
# Load .env from the omniflow directory
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    OPENAI_API_KEY: str = Field(default="",env="OPENAI_API_KEY")


# Create global settings instance
settings = Settings()

# Set environment variable for OpenAI if available
if settings.OPENAI_API_KEY:
    os.environ['OPENAI_API_KEY'] = settings.OPENAI_API_KEY
