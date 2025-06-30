"""End-to-end test for HL7 message processing flow."""
import asyncio
import json
import os
import pytest
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest_asyncio
import httpx

from integration_engine.core.queues.queue_manager import QueueManager
from integration_engine.services.input.hl7v2_listener import HL7v2Listener
from integration_engine.services.processing.validation_service import ValidationService
from integration_engine.services.processing.transformation_service import TransformationService
from integration_engine.services.processing.routing_service import RoutingService
from integration_engine.services.outbound.fhir_sender import FHIROutboundSender

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "data"
SAMPLE_HL7_FILE = TEST_DATA_DIR / "sample_hl7_message.txt"

@pytest.fixture
def sample_hl7_message():
    """Load sample HL7 message from file."""
    try:
        with open(SAMPLE_HL7_FILE, "r") as f:
            content = f.read()
            logger.info(f"Loaded HL7 message from {SAMPLE_HL7_FILE}")
            return content
    except Exception as e:
        logger.error(f"Error loading HL7 message: {e}")
        raise

@pytest.fixture
async def queue_manager():
    """Create and return a QueueManager instance."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    manager = QueueManager(host=redis_host, port=redis_port, db=1)  # Use DB 1 for testing
    try:
        await manager.initialize()
        logger.info(f"Initialized QueueManager with Redis at {redis_host}:{redis_port}")
        yield manager
    finally:
        await manager.shutdown()
        logger.info("Shut down QueueManager")

@pytest.fixture
async def hl7_listener(queue_manager):
    """Create and return an HL7v2Listener instance."""
    # Create a temporary directory for file watcher
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    input_dir = os.path.join(temp_dir, "input")
    processed_dir = os.path.join(temp_dir, "processed")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    
    listener = HL7v2Listener(
        queue_manager=queue_manager,
        output_queue="validation",
        file_watcher_config={
            "input_dir": input_dir,
            "processed_dir": processed_dir,
            "poll_interval": 1
        }
    )
    await listener.start()
    yield listener
    await listener.stop()
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
async def validation_service(queue_manager):
    """Create and return a ValidationService instance."""
    service = ValidationService(
        queue_manager=queue_manager,
        input_queue="validation",
        output_queue="transformation"
    )
    await service.start()
    yield service
    await service.stop()

@pytest.fixture
async def transformation_service(queue_manager):
    """Create and return a TransformationService instance."""
    service = TransformationService(
        queue_manager=queue_manager,
        input_queue="transformation",
        output_queue="routing"
    )
    await service.start()
    yield service
    await service.stop()

@pytest.fixture
async def routing_service(queue_manager):
    """Create and return a RoutingService instance."""
    service = RoutingService(
        queue_manager=queue_manager,
        input_queue="routing",
        default_route="fhir_messages"
    )
    await service.start()
    yield service
    await service.stop()

@pytest.fixture
async def fhir_sender(queue_manager):
    """Create and return a FHIROutboundSender instance."""
    fhir_base_url = os.getenv("FHIR_SERVER_URL", "http://mock-fhir-server:8080/fhir")
    logger.info(f"Initializing FHIROutboundSender with FHIR server at {fhir_base_url}")
    
    # Create server config with required base_url
    server_config = {
        "base_url": fhir_base_url,
        "auth_type": "none"
    }
    
    sender = FHIROutboundSender(
        server_config=server_config,
        queue_manager=queue_manager,
        input_queue="fhir_messages"
    )
    await sender.initialize()
    try:
        yield sender
    finally:
        await sender.shutdown()

@pytest.mark.asyncio
async def test_end_to_end_hl7_flow(
    sample_hl7_message,
    queue_manager,
    hl7_listener,
    validation_service,
    transformation_service,
    routing_service,
    fhir_sender
):
    """Test end-to-end HL7 message processing flow."""
    # Clear any existing messages from the queues
    for queue in ["hl7_inbound", "validation", "transformation", "routing", "fhir_messages"]:
        await queue_manager.redis.delete(queue)
    
    # Start all services
    logger.info("Starting all services...")
    await asyncio.gather(
        hl7_listener.start(),
        validation_service.start(),
        transformation_service.start(),
        routing_service.start(),
        fhir_sender.start()
    )
    
    try:
        # Create a test client for the mock FHIR server
        fhir_base_url = os.getenv("FHIR_SERVER_URL", "http://mock-fhir-server:8080/fhir")
        async with httpx.AsyncClient() as client:
            # Verify the FHIR server is accessible
            try:
                response = await client.get(f"{fhir_base_url}/metadata")
                response.raise_for_status()
                logger.info("Successfully connected to FHIR server")
            except Exception as e:
                logger.error(f"Failed to connect to FHIR server at {fhir_base_url}: {e}")
                pytest.fail(f"FHIR server not available: {e}")
            
            # Send HL7 message to the input queue
            logger.info("Sending HL7 message to input queue...")
            message_data = {
                "message": sample_hl7_message,
                "metadata": {
                    "message_type": "HL7v2",
                    "message_control_id": "MSG00001",
                    "sending_application": "SENDING_APP",
                    "sending_facility": "SENDING_FACILITY",
                    "receiving_application": "RECEIVING_APP",
                    "receiving_facility": "RECEIVING_FACILITY",
                    "message_datetime": "2023-06-29T12:00:00Z"
                }
            }
            await queue_manager.publish("hl7_inbound", message_data)
            
            # Wait for the message to be processed (with timeout)
            logger.info("Waiting for message processing...")
            max_attempts = 10
            for attempt in range(max_attempts):
                # Check if the message reached the FHIR server
                try:
                    # Query the FHIR server for the patient
                    search_url = f"{fhir_base_url}/Patient?family=Doe&given=John"
                    search_response = await client.get(search_url)
                    search_response.raise_for_status()
                    
                    bundle = search_response.json()
                    if bundle.get("total", 0) > 0:
                        logger.info("Patient record found in FHIR server")
                        patient = bundle["entry"][0]["resource"]
                        assert patient["name"][0]["family"] == "Doe"
                        assert patient["name"][0]["given"] == ["John", "A"]
                        break
                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1}: Patient not found yet: {e}")
                
                await asyncio.sleep(1)
            else:
                pytest.fail("Timeout waiting for message to be processed")
            
            logger.info("Message processing completed successfully")
            
    finally:
        # Stop all services
        logger.info("Stopping all services...")
        try:
            await asyncio.gather(
                hl7_listener.stop(),
                validation_service.stop(),
                transformation_service.stop(),
                routing_service.stop(),
                fhir_sender.stop(),
                return_exceptions=True  # Don't fail if some services are already stopped
            )
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")
            raise
