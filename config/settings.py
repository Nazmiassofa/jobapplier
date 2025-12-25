import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, ClassVar
from dotenv import load_dotenv

load_dotenv()

@dataclass(slots=True)
class Settings:
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: Optional[str] = os.getenv("DB_NAME")
    DB_USER: Optional[str] = os.getenv("DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("DB_PASSWORD")

    # Emails
    SMTP_SERVER: Optional[str] = os.getenv("SMTP_SERVER")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    DEV_EMAIL: Optional[str] = os.getenv("DEV_EMAIL")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "DEV")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Class variable 
    BASE_DIR: ClassVar[Path] = Path(__file__).resolve().parent.parent

    def __post_init__(self) -> None:
        if self.ENVIRONMENT != "DEV":
            required = {
                "DB_NAME": self.DB_NAME,
                "DB_USER": self.DB_USER,
                "DB_PASSWORD": self.DB_PASSWORD,
                "SMTP_SERVER": self.SMTP_SERVER,
                "REDIS_HOST": self.REDIS_HOST,
                "REDIS_PASSWORD": self.REDIS_PASSWORD,
            }
            missing = [k for k, v in required.items() if not v]
            if missing:
                raise RuntimeError(
                    f"Missing required environment variables: {', '.join(missing)}"
                )


config = Settings()
