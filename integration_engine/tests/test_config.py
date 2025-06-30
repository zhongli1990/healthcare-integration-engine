"""Test configuration for integration engine tests."""
from pydantic import BaseModel, Field


class RedisConfig(BaseModel):
    """Redis configuration for tests."""
    host: str = "redis-test"
    port: int = 6379
    db: int = 0
    password: str = ""
    ssl: bool = False


class QueueConfig(BaseModel):
    """Queue configuration for tests."""
    redis: RedisConfig = Field(default_factory=RedisConfig)


class TestConfig(BaseModel):
    """Test configuration."""
    environment: str = "test"
    log_level: str = "INFO"
    queues: QueueConfig = Field(default_factory=QueueConfig)
    
    # Test data paths
    test_data_dir: str = "/app/tests/data"
    input_dir: str = "/app/tests/data/inputs"
    output_dir: str = "/app/tests/data/outputs"
    processed_dir: str = "/app/tests/data/processed"
    errors_dir: str = "/app/tests/data/errors"


def get_test_config() -> TestConfig:
    """Get test configuration."""
    return TestConfig()
