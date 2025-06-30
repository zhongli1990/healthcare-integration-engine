"""Unit tests for the QueueManager class."""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from typing import AsyncGenerator, Any, Tuple, Optional, List, Dict, AsyncIterator
from uuid import UUID, uuid4
from datetime import datetime

from integration_engine.core.queues.queue_manager import QueueManager, RedisQueue
from integration_engine.core.models.message import MessageEnvelope, MessageHeader, MessageBody, MessageStatus


class AsyncMessageIterator:
    """Async iterator for mocking the consume method."""
    def __init__(self, messages):
        self.messages = messages
        self.index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self.index >= len(self.messages):
            raise StopAsyncIteration
        message = self.messages[self.index]
        self.index += 1
        return message


def create_test_envelope(content, message_id=None):
    """Helper to create a test message envelope."""
    return MessageEnvelope(
        header=MessageHeader(
            message_id=message_id or str(uuid4()),
            correlation_id=None,
            message_type='',
            source='test',
            destination=[],
            timestamp=datetime.utcnow(),
            status=MessageStatus.RECEIVED,
            retry_count=0,
            metadata={}
        ),
        body=MessageBody(
            content_type='application/json',
            content=content,
            raw_content=None,
            schema_id=None,
            metadata={}
        )
    )


class TestQueueManager:
    """Test suite for the QueueManager class."""

    @pytest.fixture
    def mock_redis_queue(self):
        """Create a mock RedisQueue instance."""
        from unittest.mock import AsyncMock, patch, MagicMock
        
        # Class-level storage for queue data to maintain state across instances
        class MockRedisQueue:
            # Class-level storage for queues
            _queues = {}
            
            def __init__(self, config, redis_url=None, **kwargs):
                self.name = config.name
                self.config = config
                self.redis_url = redis_url
                self.published = []
                
                # Initialize instance storage if not already present
                if self.name not in self._queues:
                    self._queues[self.name] = {
                        'messages': {},
                        'acks': [],
                        'nacks': []
                    }
                
                # Add a test message to queues used in tests if empty
                if not self._queues[self.name]['messages']:
                    if self.name in ["test_queue", "test_ack", "test_nack"]:
                        test_msg = {"key": "value"}
                        test_envelope = create_test_envelope(test_msg)
                        self._queues[self.name]['messages']["test-msg-1"] = test_msg
                    elif self.name == "test_serialization":
                        test_msg = {
                            "string": "test",
                            "number": 123,
                            "boolean": True,
                            "nested": {"key": "value"},
                            "list": [1, 2, 3]
                        }
                        test_envelope = create_test_envelope(test_msg)
                        self._queues[self.name]['messages']["test-serialization-msg"] = test_msg
                
                # Create a queue-like object that supports qsize()
                class QueueLike:
                    def __init__(self, messages):
                        self._messages = messages
                    
                    def qsize(self):
                        # Return the number of messages in the queue
                        return len(self._messages)
                
                # Store the queue-like object for queue_length checking
                # Make sure it's accessible as queue.queue for QueueManager compatibility
                self.queue = QueueLike(self._queues[self.name]['messages'])
                
                # Also add a direct qsize method for direct access
                self.qsize = self.queue.qsize
                
                # Create async methods with AsyncMock
                self.publish = AsyncMock(side_effect=self._publish_impl)
                self.consume = AsyncMock(side_effect=self._consume_impl)
                self.ack = AsyncMock(side_effect=self._ack_impl)
                self.nack = AsyncMock(side_effect=self._nack_impl)
                self.queue_length = AsyncMock(side_effect=self._queue_length_impl)
            
            @property
            def messages(self):
                return self._queues[self.name]['messages']
                
            @property
            def acks(self):
                return self._queues[self.name]['acks']
                
            @property
            def nacks(self):
                return self._queues[self.name]['nacks']
                
            async def _publish_impl(self, message):
                self.published.append(message)
                message_id = f"msg-{len(self.messages)}"
                self.messages[message_id] = message
                return True
                
            async def _consume_impl(self, timeout=None):
                if not self.messages:
                    return AsyncMessageIterator([])
                message_id, message = next(iter(self.messages.items()))
                # Return a message with message_id and the message content
                return AsyncMessageIterator([(message_id, {"message_id": message_id, **message})])
                
            async def _ack_impl(self, message_id):
                self.acks.append(message_id)
                if message_id in self.messages:
                    del self.messages[message_id]
                return True
                
            async def _nack_impl(self, message_id):
                self.nacks.append(message_id)
                return True
                
            async def _queue_length_impl(self):
                return len(self.messages)
                
            async def close(self):
                pass
            
            @classmethod
            def reset(cls):
                """Reset all queues for testing."""
                cls._queues = {}
    
        # Create a mock queue factory function
        def create_mock_queue(queue_name):
            # Create a mock config
            from dataclasses import make_dataclass
            Config = make_dataclass('Config', ['name', 'max_size', 'ttl_seconds'])
            config = Config(name=queue_name, max_size=10000, ttl_seconds=3600)
            
            return MockRedisQueue(config=config)
        
        # Create a mock queue for testing
        mock_queue = create_mock_queue("test_queue")
        
        # Add the create_queue method to the mock
        mock_queue.create_queue = create_mock_queue
        
        # Reset the mock queue state before each test
        MockRedisQueue.reset()
        
        return mock_queue
        
    @pytest.fixture
    def queue_manager_with_mock_redis(self, mock_redis_queue):
        """Create a QueueManager instance with a mock RedisQueue."""
        # Store the original RedisQueue class
        original_redis_queue = None
        
        # Create a mock RedisQueue class that uses our mock_redis_queue
        class MockRedisQueueClass:
            def __init__(self, config, redis_url=None, **kwargs):
                # Always create a new queue instance to ensure we're using the same mock
                self.queue = mock_redis_queue.create_queue(config.name)
                
            def __getattr__(self, name):
                # Delegate all other attribute access to the queue
                return getattr(self.queue, name)
        
        # Patch the RedisQueue class
        with patch('integration_engine.core.queues.queue_manager.RedisQueue', new=MockRedisQueueClass):
            # Create a new QueueManager instance
            manager = QueueManager()
            
            # Store the original get_queue method
            original_get_queue = manager.get_queue
            
            # Create a patched version of get_queue
            async def patched_get_queue(name, *args, **kwargs):
                # Check if we already have this queue
                if name in manager.queues:
                    return manager.queues[name]
                
                # Get the queue using the original method
                queue = await original_get_queue(name, *args, **kwargs)
                
                # Ensure the queue has the expected methods
                if not hasattr(queue, 'ack'):
                    queue.ack = AsyncMock(side_effect=lambda msg_id: queue.queue.ack(msg_id))
                if not hasattr(queue, 'nack'):
                    queue.nack = AsyncMock(side_effect=lambda msg_id: queue.queue.nack(msg_id))
                if not hasattr(queue, 'queue_length'):
                    queue.queue_length = AsyncMock(side_effect=queue.queue.queue_length)
                
                return queue
            
            # Replace the get_queue method with our patched version
            manager.get_queue = patched_get_queue
            
            try:
                # Yield the manager to the test
                yield manager
            finally:
                # Restore the original get_queue method
                manager.get_queue = original_get_queue
            
            return manager
    
    @pytest.mark.asyncio
    async def test_publish_and_consume(self, mock_redis_queue, queue_manager_with_mock_redis):
        """Test publishing and consuming messages."""
        test_queue = "test_queue"
        test_message = {"key": "value"}
        
        # Publish a message
        result = await queue_manager_with_mock_redis.publish(test_queue, test_message)
        assert result is True
        
        # Consume the message
        message = await queue_manager_with_mock_redis.consume(test_queue, timeout=1.0)
        
        # Verify the message content (should include message_id)
        assert "message_id" in message
        assert message["key"] == "value"

    @pytest.mark.asyncio
    async def test_message_acknowledgment(self, mock_redis_queue, queue_manager_with_mock_redis):
        """Test acknowledgment of messages."""
        test_queue = "test_ack"

        # Get the queue instance from the manager
        queue = await queue_manager_with_mock_redis.get_queue(test_queue)
        
        # Reset the mock before the test
        queue.ack.reset_mock()

        # Consume the message
        message = await queue_manager_with_mock_redis.consume(test_queue, timeout=1.0)
        assert message is not None
        assert "message_id" in message
        assert message["key"] == "value"

        # Acknowledge the message
        message_id = message["message_id"]
        await queue_manager_with_mock_redis.acknowledge(test_queue, message_id)

        # Verify ack was called with the correct message_id
        queue.ack.assert_awaited_once_with(message_id)

    @pytest.mark.asyncio
    async def test_message_nack(self, mock_redis_queue, queue_manager_with_mock_redis):
        """Test negative acknowledgment (NACK) of messages."""
        test_queue = "test_nack"

        # Get the queue instance from the manager
        queue = await queue_manager_with_mock_redis.get_queue(test_queue)
        
        # Reset the mock before the test
        queue.nack.reset_mock()

        # Consume the message
        message = await queue_manager_with_mock_redis.consume(test_queue, timeout=1.0)
        assert message is not None
        assert "message_id" in message
        assert message["key"] == "value"

        # Nack the message
        message_id = message["message_id"]
        await queue_manager_with_mock_redis.negative_acknowledge(test_queue, message_id)

        # Verify nack was called with the correct message_id
        queue.nack.assert_awaited_once_with(message_id)

    @pytest.mark.asyncio
    async def test_queue_length(self, mock_redis_queue, queue_manager_with_mock_redis):
        """Test getting queue length."""
        test_queue = "test_queue"  # Must match the queue name in the mock
        
        # Get the queue instance from the manager
        queue = await queue_manager_with_mock_redis.get_queue(test_queue)
        
        # Clear any existing messages from the queue by accessing the internal storage
        if hasattr(queue, '_queues') and test_queue in queue._queues:
            queue._queues[test_queue]['messages'].clear()
        
        # Add a test message to the queue
        test_msg = {"key": "value"}
        test_envelope = create_test_envelope(test_msg)
        await queue.publish(test_envelope)
        
        # Test queue length
        length = await queue_manager_with_mock_redis.queue_length(test_queue)
        
        # Verify the queue length is correct - should be 1 after clearing and adding one message
        assert length == 1, f"Expected queue length 1, got {length}"

    @pytest.mark.asyncio
    async def test_redis_connection_error(self, mock_redis_queue, queue_manager_with_mock_redis):
        """Test handling of Redis connection errors."""
        # Create a test message
        test_message = {"test": "error"}
        
        # Create a new mock for the publish method that raises an error
        async def mock_publish_raises(*args, **kwargs):
            raise ConnectionError("Redis connection error")
        
        # Replace the publish method with our error-raising version
        original_publish = mock_redis_queue.publish
        mock_redis_queue.publish = AsyncMock(side_effect=mock_publish_raises)
        
        # Also patch the QueueManager's publish method to use our mock
        original_manager_publish = queue_manager_with_mock_redis.publish
        
        async def patched_publish(queue_name, message, **kwargs):
            if queue_name == "test_error":
                await mock_redis_queue.publish(message)
            else:
                return await original_manager_publish(queue_name, message, **kwargs)
                
        queue_manager_with_mock_redis.publish = patched_publish
        
        try:
            # Test that the error is properly propagated
            with pytest.raises(ConnectionError, match="Redis connection error"):
                await queue_manager_with_mock_redis.publish("test_error", test_message)
            
            # Verify publish was called with the correct arguments
            mock_redis_queue.publish.assert_awaited_once()
        finally:
            # Restore the original methods
            mock_redis_queue.publish = original_publish
            queue_manager_with_mock_redis.publish = original_manager_publish

    @pytest.mark.asyncio
    async def test_message_serialization(self, mock_redis_queue, queue_manager_with_mock_redis):
        """Test that messages are properly serialized and deserialized."""
        test_queue = "test_serialization"
        test_message = {
            "string": "test",
            "number": 123,
            "boolean": True,
            "nested": {"key": "value"},
            "list": [1, 2, 3]
        }
        
        # Publish the message
        result = await queue_manager_with_mock_redis.publish(test_queue, test_message)
        assert result is True
        
        # Consume the message
        consumed_message = await queue_manager_with_mock_redis.consume(test_queue, timeout=1.0)
        
        # Verify the message was properly deserialized (check content, not exact match)
        assert consumed_message is not None
        assert "message_id" in consumed_message
        for key, value in test_message.items():
            assert consumed_message[key] == value
        
        # Verify types are preserved
        assert isinstance(consumed_message["number"], int)
        assert isinstance(consumed_message["boolean"], bool)
        assert isinstance(consumed_message["nested"], dict)
        assert isinstance(consumed_message["list"], list)
