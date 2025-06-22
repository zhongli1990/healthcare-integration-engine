from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    PROJECT_NAME: str = "Healthcare Integration Engine"
    VERSION: str = "1.0.0"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "healthcare_integration"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost/healthcare_integration"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8851"]
    TRUSTED_HOSTS: List[str] = ["localhost"]

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8850

    # JWT
    JWT_SECRET: str = "your-jwt-secret-here"

    # Sentry
    SENTRY_DSN: str = "your-sentry-dsn-here"

    # HL7 Settings
    HL7_SERVER_HOST: str = "localhost"
    HL7_PORT: int = 2575
    
    # HL7 File Processing
    HL7_WATCH_DIR: str = "./data/hl7/incoming"
    HL7_PROCESSED_DIR: str = "./data/hl7/processed"
    HL7_ERROR_DIR: str = "./data/hl7/errors"
    HL7_FILE_PATTERN: str = "*.hl7"
    HL7_POLL_INTERVAL: int = 5  # seconds

    # DICOM
    DICOM_SERVER_HOST: str = "localhost"
    DICOM_AE_TITLE: str = "HEALTHCARE"
    DICOM_PORT: int = 11112

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # SMTP
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "your-email@example.com"
    SMTP_PASSWORD: str = "your-email-password"
    EMAIL_FROM: str = "healthcare@example.com"

    class Config:
        case_sensitive = True
        env_file = ".env"

    @property
    def get_database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
