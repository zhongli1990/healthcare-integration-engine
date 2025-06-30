"""End-to-end tests for HL7 workflow."""
import asyncio
import json
import os
import socket
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import aiofiles
from aiohttp import ClientSession

from integration_engine.core.queues.queue_manager import QueueManager
from integration_engine.core.models.message import MessageEnvelope, MessageHeader, MessageBody, MessageStatus

# Test configuration
TEST_DATA_DIR = Path(__file__).parent.parent / "data"
HL7_MESSAGES_DIR = TEST_DATA_DIR / "hl7_messages"
OUTPUT_DIR = TEST_DATA_DIR / "outputs"
PROCESSED_DIR = TEST_DATA_DIR / "processed"
ERRORS_DIR = TEST_DATA_DIR / "errors"

# Ensure test directories exist
for directory in [OUTPUT_DIR, PROCESSED_DIR, ERRORS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def queue_manager():
    """Create a QueueManager instance for testing."""
    manager = QueueManager(redis_url="redis://localhost:6379/0")
    yield manager
    await manager.close()

class TestHL7Workflow:
    """Test suite for HL7 workflow scenarios."""

    @pytest.mark.asyncio
    async def test_hl7_mllp_workflow(self, queue_manager):
        """Test end-to-end HL7 MLLP workflow."""
        # Setup test data
        test_message = (HL7_MESSAGES_DIR / "adt_a01.hl7").read_text()
        
        # Send HL7 message via MLLP
        mllp_start = '\x0b'
        mllp_end = '\x1c\r'
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 2575))
            s.sendall(f"{mllp_start}{test_message}{mllp_end}".encode())
            response = s.recv(1024)
            assert response == b'\x06'  # ACK
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Verify output
        output_files = list(OUTPUT_DIR.glob("*.hl7"))
        assert len(output_files) > 0, "No output files found"
        
        # Verify message content
        output_content = output_files[0].read_text()
        assert "MSH|^~\&|" in output_content
        assert "ADT^A01" in output_content
        
        # Cleanup
        output_files[0].unlink()

    @pytest.mark.asyncio
    async def test_hl7_file_workflow(self, queue_manager):
        """Test end-to-end HL7 file workflow."""
        # Setup test data
        test_file = PROCESSED_DIR / "test_file.hl7"
        test_message = (HL7_MESSAGES_DIR / "adt_a04.hl7").read_text()
        
        # Write test file
        async with aiofiles.open(test_file, 'w') as f:
            await f.write(test_message)
        
        # Wait for file processing
        max_attempts = 10
        processed = False
        for _ in range(max_attempts):
            if not test_file.exists():
                processed = True
                break
            await asyncio.sleep(1)
        
        assert processed, "File was not processed"
        
        # Verify output
        output_files = list(OUTPUT_DIR.glob("*_file.hl7"))
        assert len(output_files) > 0, "No output files found"
        
        # Verify message content
        output_content = output_files[0].read_text()
        assert "MSH|^~\&|" in output_content
        assert "ADT^A04" in output_content
        
        # Cleanup
        output_files[0].unlink()

    @pytest.mark.asyncio
    async def test_error_handling(self, queue_manager):
        """Test error handling for invalid HL7 messages."""
        # Send invalid HL7 message
        invalid_message = "INVALID HL7 MESSAGE"
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 2575))
            s.sendall(f"\x0b{invalid_message}\x1c\r".encode())
            response = s.recv(1024)
            assert response == b'\x15'  # NACK
        
        # Verify error file was created
        error_files = list(ERRORS_DIR.glob("*.err"))
        assert len(error_files) > 0, "No error files found"
        
        # Verify error content
        error_content = error_files[0].read_text()
        assert "Invalid HL7 message" in error_content
        
        # Cleanup
        error_files[0].unlink()

    @pytest.mark.asyncio
    async def test_message_acknowledgment(self, queue_manager):
        """Test message acknowledgment flow."""
        # Publish a test message directly to the queue
        test_message = (HL7_MESSAGES_DIR / "adt_a01.hl7").read_text()
        
        # Create message envelope
        envelope = MessageEnvelope(
            header=MessageHeader(
                message_id="test_msg_123",
                message_type="ADT^A01",
                source_system="test_system",
                destination_systems=["output_system"],
                timestamp=time.time(),
                status=MessageStatus.RECEIVED
            ),
            body=MessageBody(
                content=test_message,
                content_type="application/hl7-v2"
            )
        )
        
        # Publish to input queue
        queue = await queue_manager.get_queue("raw_messages")
        await queue.publish(envelope.model_dump_json())
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Verify output
        output_files = list(OUTPUT_DIR.glob("*.hl7"))
        assert len(output_files) > 0, "No output files found"
        
        # Cleanup
        output_files[0].unlink()

    @pytest.mark.asyncio
    async def test_high_volume(self, queue_manager):
        """Test processing of multiple messages."""
        # Send multiple messages
        num_messages = 10
        test_message = (HL7_MESSAGES_DIR / "adt_a01.hl7").read_text()
        
        for i in range(num_messages):
            # Create unique message ID
            msg_id = f"test_msg_{i}"
            
            # Create message envelope
            envelope = MessageEnvelope(
                header=MessageHeader(
                    message_id=msg_id,
                    message_type="ADT^A01",
                    source_system="test_system",
                    destination_systems=["output_system"],
                    timestamp=time.time(),
                    status=MessageStatus.RECEIVED
                ),
                body=MessageBody(
                    content=test_message.replace("MSG00001", f"MSG{i:05d}"),
                    content_type="application/hl7-v2"
                )
            )
            
            # Publish to input queue
            queue = await queue_manager.get_queue("raw_messages")
            await queue.publish(envelope.model_dump_json())
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Verify output
        output_files = list(OUTPUT_DIR.glob("*.hl7"))
        assert len(output_files) == num_messages, f"Expected {num_messages} output files, got {len(output_files)}"
        
        # Cleanup
        for file in output_files:
            file.unlink()
