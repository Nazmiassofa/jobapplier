import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", None)
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = os.getenv("DB_PORT", 5432)
    DB_NAME: str = os.getenv("DB_NAME")
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    
    # Emails
    SMTP_SERVER: str = os.getenv("SMTP_SERVER")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    DEV_EMAIL: str = os.getenv("DEV_EMAIL")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "DEV")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    BASE_DIR = Path(__file__).resolve().parent.parent

config = Settings()