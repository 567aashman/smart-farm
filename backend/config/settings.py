"""
SmartFarm - Configuration
Loads and validates all environment variables.
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/smartfarm"
    
    @field_validator("database_url", mode="before")
    def fix_postgres_url(cls, v):
        if isinstance(v, str):
            v = v.strip().strip("'").strip('"')
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql://", 1)
        return v

    # AI
    groq_api_key: str = ""
    tavily_api_key: str = ""

    # Weather
    weather_api_key: str = ""
    weather_api_base: str = "https://api.openweathermap.org/data/2.5"

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    # App
    app_env: str = "development"
    app_secret_key: str = "change_this_in_production"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:5500,null"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
