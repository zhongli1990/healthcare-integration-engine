import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union, cast

import redis.asyncio as redis
from pydantic import BaseModel, Field

from integration_engine.core.models.message import MessageEnvelope, MessageHeader, MessageBody

logger = logging.getLogger(__name__)


class QueueConfig(BaseModel):
    """Configuration for a queue."""
    name: str
    max_size: int = 10000
    ttl_seconds: Optional[int] = 3600  # Time to live in seconds


class BaseQueue(ABC):
    """Abstract base class for queue implementations."""
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.name = config.name
    
    @abstractmethod
    async def publish(self, message: MessageEnvelope) -> bool:
        """Publish a message to the queue."""
        pass
    
    @abstractmethod
    async def consume(self) -> AsyncGenerator[Tuple[str, MessageEnvelope], None]:
        """Consume messages from the queue."""
        yield "", MessageEnvelope(
            header=MessageHeader(),
            body=MessageBody(content_type="")
        )  # This is just to make the linter happy
    
    @abstractmethod
    async def ack(self, message_id: str) -> None:
        """Acknowledge a message has been processed."""
        pass
    
    @abstractmethod
    async def nack(self, message_id: str) -> None:
        """Negative acknowledgment for a message."""
        pass


class InMemoryQueue(BaseQueue):
    """In-memory queue implementation using asyncio.Queue."""
    
    def __init__(self, config: QueueConfig):
        super().__init__(config)
        self.queue: asyncio.Queue[Tuple[str, MessageEnvelope]] = asyncio.Queue(maxsize=config.max_size)
        self.pending: Dict[str, asyncio.Future] = {}
    
    async def publish(self, message: MessageEnvelope) -> bool:
        """Publish a message to the queue."""
        message_id = str(message.header.message_id)
        try:
            await self.queue.put((message_id, message))
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {self.name}: {e}")
            return False
    
    async def consume(self) -> AsyncGenerator[Tuple[str, MessageEnvelope], None]:
        """Consume messages from the queue."""
        while True:
            try:
                message_id, message = await self.queue.get()
                future = asyncio.Future()
                self.pending[message_id] = future
                yield message_id, message
                await future  # Wait for ack/nack
            except Exception as e:
                logger.error(f"Error consuming message: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on error
    
    async def ack(self, message_id: str) -> None:
        """Acknowledge a message has been processed."""
        if message_id in self.pending:
            self.pending[message_id].set_result(True)
            del self.pending[message_id]
    
    async def nack(self, message_id: str) -> None:
        """Negative acknowledgment for a message."""
        if message_id in self.pending:
            self.pending[message_id].set_result(False)
            del self.pending[message_id]


class RedisQueue(BaseQueue):
    """Redis Streams based queue implementation."""
    
    def __init__(self, config: QueueConfig, redis_url: str = "redis://localhost:6379/0"):
        super().__init__(config)
        self.redis = redis.from_url(redis_url, decode_responses=False)
        self.consumer_group = f"{self.name}-group"
        self.consumer_name = f"consumer-{id(self)}"
        self._consumer_group_created = False
    
    async def _ensure_consumer_group(self):
        """Ensure the consumer group exists."""
        if not self._consumer_group_created:
            try:
                await self.redis.xgroup_create(
                    name=self.name,
                    groupname=self.consumer_group,
                    id="0",
                    mkstream=True
                )
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Failed to create consumer group: {e}")
                    raise
            self._consumer_group_created = True
    
    async def publish(self, message: MessageEnvelope) -> bool:
        """Publish a message to the queue."""
        try:
            message_dict = message.to_dict()
            # Convert UUID and datetime to strings for JSON serialization
            message_dict['header']['message_id'] = str(message_dict['header']['message_id'])
            if message_dict['header'].get('correlation_id'):
                message_dict['header']['correlation_id'] = str(message_dict['header']['correlation_id'])
            message_dict['header']['timestamp'] = message_dict['header']['timestamp']
            
            # Convert raw_content to base64 if it's bytes
            if isinstance(message_dict['body'].get('raw_content'), bytes):
                import base64
                message_dict['body']['raw_content'] = base64.b64encode(
                    message_dict['body']['raw_content']
                ).decode('utf-8')
                message_dict['body']['_raw_content_encoding'] = 'base64'
            
            message_json = json.dumps(message_dict)
            await self.redis.xadd(
                name=self.name,
                fields={"data": message_json},
                maxlen=10000,
                approximate=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to Redis: {e}")
            return False
    
    async def consume(self) -> AsyncGenerator[Tuple[str, MessageEnvelope], None]:
        """Consume messages from the queue."""
        await self._ensure_consumer_group()
        last_id = '>'
        
        while True:
            try:
                # Read messages from the stream
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.name: last_id},
                    count=1,
                    block=5000  # 5 second block
                )
                
                if not messages:
                    continue
                
                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # Convert message data back to dictionary
                            message_json = message_data[b'data'].decode('utf-8')
                            message_dict = json.loads(message_json)
                            
                            # Handle base64 encoded raw_content
                            if message_dict['body'].get('_raw_content_encoding') == 'base64' and message_dict['body'].get('raw_content'):
                                import base64
                                message_dict['body']['raw_content'] = base64.b64decode(
                                    message_dict['body']['raw_content']
                                )
                            
                            # Create MessageEnvelope from dictionary
                            message = MessageEnvelope.from_dict(message_dict)
                            yield message_id.decode('utf-8'), message
                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {e}")
                            await self.ack(message_id)
                            
            except Exception as e:
                logger.error(f"Error in Redis consumer: {e}")
                await asyncio.sleep(5)  # Backoff on error
    
    async def ack(self, message_id: str) -> None:
        """Acknowledge a message has been processed."""
        try:
            # Convert message_id to bytes if it's a string
            if isinstance(message_id, str):
                message_id = message_id.encode('utf-8')
            
            # Use the correct parameter format for xack
            await self.redis.xack(
                name=self.name,
                groupname=self.consumer_group,
                id=message_id.decode('utf-8')  # Convert back to string for redis-py
            )
        except Exception as e:
            logger.error(f"Failed to ack message {message_id}: {e}")
            raise  # Re-raise the exception to fail the test
    
    async def nack(self, message_id: str) -> None:
        """Negative acknowledgment for a message."""
        try:
            # In Redis Streams, nack is implemented by not acknowledging the message
            # The message will be redelivered after the visibility timeout
            # We'll just log the nack and let Redis handle the redelivery
            logger.debug(f"Nacking message {message_id} - will be redelivered")
            
        except Exception as e:
            logger.error(f"Failed to nack message {message_id}: {e}")
            raise  # Re-raise the exception to fail the test


class QueueManager:
    """Manages multiple queues and provides a unified interface."""
    
    def __init__(self, use_redis: bool = True, redis_url: str = None, host: str = None, port: int = 6379, db: int = 0):
        self.queues: Dict[str, BaseQueue] = {}
        self.use_redis = use_redis
        
        # Support both URL-based and host/port-based configuration
        if redis_url:
            self.redis_url = redis_url
        else:
            self.redis_url = f"redis://{host or 'localhost'}:{port}/{db}"
            
        self.redis_client = redis.Redis.from_url(self.redis_url) if use_redis else None
    
    async def initialize(self) -> None:
        """Initialize the queue manager.
        
        This method is called when the integration engine starts up to perform any
        necessary initialization of the queue manager.
        """
        logger.info("Initializing queue manager...")
        # No-op for now, but can be used for future initialization logic
        pass
    
    async def get_queue(self, name: str, config: Optional[QueueConfig] = None) -> BaseQueue:
        """Get or create a queue."""
        if name not in self.queues:
            if config is None:
                config = QueueConfig(name=name)
            
            if self.use_redis:
                self.queues[name] = RedisQueue(config, self.redis_url)
            else:
                self.queues[name] = InMemoryQueue(config)
        
        return self.queues[name]
    
    async def publish(self, queue_name: str, message: Any) -> bool:
        """Publish a message to the specified queue."""
        queue = await self.get_queue(queue_name)
        if not isinstance(message, MessageEnvelope):
            message = MessageEnvelope(
                header=MessageHeader(),
                body=MessageBody(content=message, content_type="application/json")
            )
        return await queue.publish(message)
    
    async def consume(self, queue_name: str, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Consume a message from the specified queue.
        
        Args:
            queue_name: Name of the queue to consume from
            timeout: Maximum time to wait for a message in seconds
            
        Returns:
            The message content if a message is available, None if timeout occurs
        """
        queue = await self.get_queue(queue_name)
        try:
            # Create a task for consuming a single message
            consume_task = asyncio.create_task(self._consume_single(queue))
            
            # Wait for the task to complete or timeout
            try:
                async with asyncio.timeout(timeout):
                    message = await consume_task
                    return message
            except asyncio.TimeoutError:
                # If we timed out, cancel the consume task and return None
                consume_task.cancel()
                try:
                    await consume_task
                except asyncio.CancelledError:
                    pass
                return None
                
        except Exception as e:
            logger.error(f"Error consuming from queue {queue_name}: {e}")
            raise
    
    async def _consume_single(self, queue: BaseQueue) -> Optional[Dict[str, Any]]:
        """Consume a single message from the queue.
        
        Args:
            queue: The queue to consume from
            
        Returns:
            The message content as a dictionary, or None if no message is available
            
        Raises:
            Exception: If there's an error consuming the message
        """
        try:
            # Get the async iterator from the queue's consume method
            message_iter = queue.consume()
            
            # If the result is a coroutine, await it to get the iterator
            if asyncio.iscoroutine(message_iter):
                message_iter = await message_iter
            
            # Get the first message from the iterator
            async for message_id, message in message_iter:
                if message is not None:
                    # Extract content from the message
                    if hasattr(message, 'body') and hasattr(message.body, 'content'):
                        content = message.body.content
                        if isinstance(content, (str, bytes)):
                            try:
                                content = json.loads(content)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        return {"message_id": message_id, **content}
                    elif isinstance(message, dict):
                        return {"message_id": message_id, **message}
                    return message
                break
            return None
        except Exception as e:
            logger.error(f"Error in _consume_single: {e}")
            raise
    
    async def acknowledge(self, queue_name: str, message_id: str) -> None:
        """Acknowledge that a message has been processed.
        
        Args:
            queue_name: Name of the queue the message belongs to
            message_id: ID of the message to acknowledge
            
        Raises:
            ValueError: If the queue or message ID is invalid
        """
        if not message_id:
            raise ValueError("Message ID cannot be empty")
            
        queue = await self.get_queue(queue_name)
        if not queue:
            raise ValueError(f"Queue {queue_name} not found")
            
        try:
            # Get the ack method and ensure it's a coroutine
            ack_method = queue.ack
            if asyncio.iscoroutinefunction(ack_method):
                await ack_method(message_id)
            else:
                # If it's not a coroutine, call it directly
                ack_method(message_id)
                
            logger.debug(f"Acknowledged message {message_id} from queue {queue_name}")
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id} on queue {queue_name}: {e}")
            raise
    
    async def negative_acknowledge(self, queue_name: str, message_id: str) -> None:
        """Negatively acknowledge a message (NACK).
        
        Args:
            queue_name: Name of the queue the message belongs to
            message_id: ID of the message to negatively acknowledge
            
        Raises:
            ValueError: If the queue or message ID is invalid
        """
        if not message_id:
            raise ValueError("Message ID cannot be empty")
            
        queue = await self.get_queue(queue_name)
        if not queue:
            raise ValueError(f"Queue {queue_name} not found")
            
        try:
            # Get the nack method and ensure it's a coroutine
            nack_method = queue.nack
            if asyncio.iscoroutinefunction(nack_method):
                await nack_method(message_id)
            else:
                # If it's not a coroutine, call it directly
                nack_method(message_id)
                
            logger.debug(f"Negatively acknowledged message {message_id} from queue {queue_name}")
        except Exception as e:
            logger.error(f"Failed to negatively acknowledge message {message_id} on queue {queue_name}: {e}")
            raise
    
    async def queue_length(self, queue_name: str) -> int:
        """Get the number of messages in the queue.
        
        For Redis, this returns the total number of messages in the stream.
        For in-memory queues, it returns the current queue size.
        
        Args:
            queue_name: Name of the queue to get the length of
            
        Returns:
            int: Number of messages in the queue
            
        Raises:
            Exception: If there's an error getting the queue length
        """
        queue = await self.get_queue(queue_name)
        
        try:
            # Handle InMemoryQueue
            if hasattr(queue, 'queue') and hasattr(queue.queue, 'qsize'):
                return queue.queue.qsize()
                
            # Handle RedisQueue
            if hasattr(queue, 'redis') and hasattr(queue, 'name'):
                try:
                    return await queue.redis.xlen(queue.name)
                except Exception as e:
                    logger.error(f"Error getting length of Redis queue {queue_name}: {e}")
                    raise
                    
            # Handle other queue types or fallback
            logger.warning(f"Queue {queue_name} does not support queue length checking")
            return 0
            
        except Exception as e:
            logger.error(f"Error getting queue length for {queue_name}: {e}")
            raise
    
    async def close(self):
        """Close all queues and clean up resources."""
        for queue in self.queues.values():
            if hasattr(queue, 'close'):
                await queue.close()
        if self.redis_client:
            await self.redis_client.aclose()
        self.queues.clear()
    
    # Alias for backward compatibility
    shutdown = close
