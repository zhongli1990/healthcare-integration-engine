"""End-to-end test for HL7 message processing flow."""
import asyncio
import json
import os
import pytest
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

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
    # Create a mock for FHIRServerConfig to bypass URL validation
    mock_config = MagicMock()
    mock_config.base_url = "http://test-fhir-server.com/fhir"
    mock_config.auth_type = "none"
    mock_config.timeout = 30
    mock_config.verify_ssl = True
    
    # Patch the FHIRServerConfig class to return our mock
    with patch('integration_engine.services.outbound.fhir_sender.FHIRServerConfig') as mock_config_class:
        mock_config_class.return_value = mock_config
        
        logger.info("Starting FHIROutboundSender with mocked FHIR server config")
        
        # Create and start sender with the mock config
        sender = FHIROutboundSender(
            server_config=mock_config,
            queue_manager=queue_manager,
            input_queue="fhir_messages"
        )
    await sender.start()
    try:
        yield sender
    finally:
        await sender.stop()

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
        if queue_manager.redis_client:
            await queue_manager.redis_client.delete(queue)
    
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
        # Publish a test message directly to the HL7 listener's queue
        test_queue = await queue_manager.get_queue("hl7_inbound")
        await test_queue.publish({
            "message_id": "test-123",
            "body": sample_hl7_message,
            "metadata": {
                "source": "test",
                "message_type": "HL7v2",
                "message_control_id": "test-123"
            }
        })
        
        # Wait for the message to be processed
        fhir_queue = await queue_manager.get_queue("fhir_messages")
        max_wait = 10  # seconds
        wait_interval = 0.5
        waited = 0
        message_processed = False
        
        while waited < max_wait and not message_processed:
            # Check if the message reached the FHIR queue
            message_count = await fhir_queue.length()
            if message_count > 0:
                message_processed = True
                break
                
            await asyncio.sleep(wait_interval)
            waited += wait_interval
        
        # Verify the message was processed
        assert message_processed, "Message was not processed within the timeout period"
        
        # Get the processed message
        message = await fhir_queue.consume()
        assert message is not None, "No message received in FHIR queue"
        
        # Verify the message structure
        assert "body" in message, "Message is missing 'body' field"
        assert "metadata" in message, "Message is missing 'metadata' field"
        assert message["metadata"].get("message_control_id") == "test-123", "Unexpected message control ID"
        
        logger.info("HL7 message was successfully processed")
        
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
