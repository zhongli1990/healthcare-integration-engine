"""Unit tests for the HL7 v2 Listener service."""
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from integration_engine.services.input.hl7v2_listener import HL7v2ListenerService, MLLPConfig, FileWatcherConfig, SFTPConfig


class MockQueueManager:
    """Mock QueueManager for testing."""
    
    def __init__(self):
        self.published_messages = []
        
    async def get_queue(self, config):
        """Mock get_queue method."""
        return self
    
    async def publish(self, queue_name, message):
        """Mock publish method."""
        self.published_messages.append((queue_name, message))
        return True


class TestHL7V2ListenerService:
    """Test suite for HL7v2ListenerService."""
    
    @pytest.fixture
    def mock_queue_manager(self):
        """Create a mock QueueManager."""
        return MockQueueManager()
    
    @pytest.fixture
    def listener_config(self, tmp_path):
        """Create a test configuration."""
        return {
            "mllp_config": {
                "host": "0.0.0.0",
                "port": 2575
            },
            "file_watcher_config": {
                "input_dir": str(tmp_path / "inputs"),
                "processed_dir": str(tmp_path / "processed"),
                "file_pattern": "*.hl7"
            },
            "sftp_config": {
                "host": "localhost",
                "port": 22,
                "username": "test",
                "password": "test",
                "remote_path": "/incoming/hl7v2",
                "local_path": str(tmp_path / "sftp"),
                "file_pattern": "*.hl7"
            }
        }
    
    @pytest.fixture
    def hl7_message(self):
        """Sample HL7 message for testing."""
        return (
            "MSH|^~\\&|SENDING_APP|SENDING_FACILITY|RECEIVING_APP|RECEIVING_FACILITY|"
            "20230629120000||ADT^A01|MSG00001|P|2.3\r"
            "EVN|A01|20230629120000|||SENDER_ID^SENDER^A^^MD^^^NPI|20230629120000\r"
            "PID|1||12345||Doe^John^A^^MR||19700101|M||2106-3|123 MAIN ST^^BOSTON^MA^02118||"
            "555-555-1234|555-555-5678||S||123-45-6789|123-45-6789\r"
        )
    
    @pytest.mark.asyncio
    async def test_process_hl7_message(self, mock_queue_manager, listener_config, hl7_message):
        """Test processing an HL7 message."""
        # Create listener with mock queue manager
        listener = HL7v2ListenerService(
            queue_manager=mock_queue_manager,
            output_queue="test_queue",
            **listener_config
        )
        
        # Process a test message with required source argument
        await listener._process_hl7_message(hl7_message, source="test_source")
        
        # Verify message was published to the queue
        assert len(mock_queue_manager.published_messages) == 1
        queue_name, message = mock_queue_manager.published_messages[0]
        assert queue_name == "test_queue"
        assert "MSH|^~\\&|SENDING_APP" in message
    
    @pytest.mark.asyncio
    async def test_file_watcher_processing(self, mock_queue_manager, listener_config, tmp_path, hl7_message):
        """Test file watcher processing of HL7 files."""
        # Create test directories
        input_dir = Path(listener_config["file_watcher_config"]["input_dir"])
        processed_dir = Path(listener_config["file_watcher_config"]["processed_dir"])
        
        input_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test HL7 file
        test_file = input_dir / "test.hl7"
        test_file.write_text(hl7_message)
        
        # Create and start listener
        listener = HL7v2ListenerService(
            queue_manager=mock_queue_manager,
            output_queue="test_queue",
            **listener_config
        )
        
        # Process the file
        await listener._process_file(test_file)
        
        # Verify message was published
        assert len(mock_queue_manager.published_messages) == 1
        
        # Verify file was moved to processed directory
        assert not test_file.exists()
        assert (processed_dir / test_file.name).exists()
    
    @pytest.mark.asyncio
    async def test_mllp_listener(self, mock_queue_manager, listener_config, hl7_message):
        """Test MLLP listener functionality."""
        # Create listener with mock queue manager
        listener = HL7v2ListenerService(
            queue_manager=mock_queue_manager,
            output_queue="test_queue",
            **listener_config
        )
        
        # Create a mock server coroutine
        async def mock_server_coro():
            return MagicMock()
            
        # Create a mock server object with serve_forever that we can control
        mock_server = MagicMock()
        mock_server.serve_forever = AsyncMock()
        
        # Patch start_server to return our mock server
        with patch('asyncio.start_server', return_value=mock_server_coro()) as mock_start_server:
            # Start the MLLP listener in the background
            listener_task = asyncio.create_task(listener._start_mllp_listener())
            
            # Give it a moment to start
            await asyncio.sleep(0.1)
            
            # Verify server was started
            mock_start_server.assert_called_once()
            
            # Simulate receiving a message
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            
            # Mock the read sequence for MLLP message
            async def mock_read(n):
                if not hasattr(mock_read, 'called'):
                    mock_read.called = True
                    return b"\x0b" + hl7_message.encode()
                return b"\x1c\r"
                
            mock_reader.read = mock_read
            
            # Call the connection handler directly
            await listener._handle_mllp_connection(mock_reader, mock_writer)
            
            # Verify message was processed
            assert len(mock_queue_manager.published_messages) == 1
            
            # Clean up
            mock_server.close = AsyncMock()
            mock_server.wait_closed = AsyncMock(return_value=True)
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
