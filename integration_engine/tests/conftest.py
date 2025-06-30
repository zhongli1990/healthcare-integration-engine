"""Pytest configuration and fixtures for integration engine tests."""
import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from integration_engine.core.config import get_config, load_config
from integration_engine.core.queues.queue_manager import QueueManager
from integration_engine.tests.test_config import get_test_config

# Add the project root to the Python path
TEST_DIR = Path(__file__).parent
ROOT_DIR = TEST_DIR.parent
DATA_DIR = TEST_DIR / "data"

# Ensure test data directories exist
os.makedirs(DATA_DIR / "inputs", exist_ok=True)
os.makedirs(DATA_DIR / "outputs", exist_ok=True)
os.makedirs(DATA_DIR / "processed", exist_ok=True)
os.makedirs(DATA_DIR / "errors", exist_ok=True)


def load_test_data(filename: str) -> Dict[str, Any]:
    """Load test data from JSON file."""
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration."""
    config = get_test_config()
    # Override any test-specific settings here if needed
    return config


@pytest_asyncio.fixture(scope="function")
async def redis_client(test_config) -> AsyncGenerator[Redis, None]:
    """Fixture providing a Redis client."""
    redis_config = test_config.queues.redis
    redis_url = f"redis://{redis_config.host}:{redis_config.port}"
    redis = Redis.from_url(redis_url, decode_responses=False, socket_connect_timeout=5, socket_timeout=5)
    try:
        # Test connection with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await redis.ping()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ConnectionError(f"Failed to connect to Redis at {redis_url} after {max_retries} attempts: {e}")
                await asyncio.sleep(1)
        yield redis
    finally:
        try:
            await redis.flushdb()
            await redis.close()
        except Exception as e:
            print(f"Error cleaning up Redis client: {e}")


@pytest_asyncio.fixture(scope="function")
async def queue_manager(test_config) -> AsyncGenerator[QueueManager, None]:
    """Fixture providing a QueueManager instance."""
    redis_config = test_config.queues.redis
    redis_url = f"redis://{redis_config.host}:{redis_config.port}"
    manager = QueueManager(use_redis=True, redis_url=redis_url)
    try:
        yield manager
    finally:
        await manager.close()
        await manager.shutdown()


@pytest.fixture(scope="session")
def hl7_sample_message() -> str:
    """Sample HL7 v2 message for testing."""
    return (
        "MSH|^~\\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|"
        "20230629120000||ADT^A01|MSG00001|P|2.3\r"
        "EVN|A01|20230629120000|||^GRAINGER^JOHN^M^JR^DR^MD^PHD^SOME^LONG^TAG^HERE^TO^TEST^PARSING||||"
        "PID|1||12345||Doe^John^^^Mr.||19700101|M||2106-3|123 Main St^^Anytown^CA^12345^USA^P||555-555-1234|555-555-5678||ENG|S|M||123-45-6789||"
    )


@pytest.fixture(scope="session")
def fhir_sample_patient() -> Dict[str, Any]:
    """Sample FHIR Patient resource for testing."""
    return {
        "resourceType": "Patient",
        "id": "example",
        "text": {
            "status": "generated",
            "div": "<div>John Doe</div>"
        },
        "identifier": [{
            "use": "usual",
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                    "code": "MR"
                }]
            },
            "system": "urn:oid:1.2.36.146.595.217.0.1",
            "value": "12345"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": "Doe",
            "given": ["John"]
        }],
        "telecom": [{
            "system": "phone",
            "value": "555-555-1234",
            "use": "home"
        }],
        "gender": "male",
        "birthDate": "1970-01-01",
        "address": [{
            "use": "home",
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",
            "country": "USA"
        }]
    }
