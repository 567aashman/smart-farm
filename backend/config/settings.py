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
    # Database (defaults to SQLite if no PostgreSQL URL is provided)
    database_url: str = ""
    
    @field_validator("database_url", mode="before")
    def fix_postgres_url(cls, v):
        if not v or not str(v).strip():
            # Check Railway-specific environment variables
            alt_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_PRIVATE_URL")
            if alt_url and alt_url.strip():
                v = alt_url.strip()
            else:
                return "sqlite:///./smartfarm.db"
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

    # Server (Railway assigns dynamic PORT)
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    @field_validator("backend_port", mode="before")
    def resolve_backend_port(cls, v):
        port_env = os.environ.get("PORT")
        if port_env and str(port_env).isdigit():
            return int(port_env)
        return v

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
