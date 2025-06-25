from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    model_config = {
        "extra": "ignore",  # Ignore extra fields in environment variables
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }
    
    # Application
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    PROJECT_NAME: str = "Healthcare Integration Engine"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "healthcare_integration")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    # Test database
    TEST_POSTGRES_SERVER: str = os.getenv("TEST_POSTGRES_SERVER", "test-db")
    TEST_POSTGRES_DB: str = os.getenv("TEST_POSTGRES_DB", "test_healthcare_integration")
    
    # Test schema name
    TEST_SCHEMA: str = "test_schema"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def TEST_DATABASE_URL(self) -> str:
        # Use the same database but with a different schema
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?options=-c%20search_path%3D{self.TEST_SCHEMA}"
    
    # For SQLAlchemy
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    TEST_SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8851"]
    TRUSTED_HOSTS: List[str] = ["localhost"]

    # Server
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8850

    # Sentry
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    
    # HL7 Settings
    HL7_SERVER_HOST: str = "localhost"
    HL7_PORT: int = 2575
    
    # HL7 File Processing
    HL7_WATCH_DIR: str = "./data/hl7/incoming"
    HL7_PROCESSED_DIR: str = "./data/hl7/processed"
    HL7_ERROR_DIR: str = "./data/hl7/errors"
    HL7_FILE_PATTERN: str = "*.hl7"
    HL7_POLL_INTERVAL: int = 5  # seconds

    # SMTP Settings
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@example.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Healthcare Integration Engine")

    # Security Headers
    SECURE_CONTENT_TYPE_NOSNIFF: bool = True
    SECURE_BROWSER_XSS_FILTER: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = True
    CSRF_COOKIE_SECURE: bool = True
    X_FRAME_OPTIONS: str = "DENY"

    # DICOM Settings
    DICOM_AE_TITLE: str = "HEALTHCARE"
    DICOM_PORT: int = 11112
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Email
    EMAIL_FROM: str = "healthcare@example.com"
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-jwt-secret-here")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    TOKEN_URL: str = "/api/v1/auth/login/access-token"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # Initialize SQLALCHEMY_DATABASE_URI
    def model_post_init(self, __context):
        self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL

# Create settings instance
settings = Settings()

# For backward compatibility
def get_settings() -> Settings:
    return settings

# Export settings as a module-level variable
__all__ = ["settings", "get_settings"]
