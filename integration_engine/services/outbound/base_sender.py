import abc
import asyncio
import logging
from typing import Any, Dict, Optional

from core.models.message import MessageEnvelope
from core.queues.queue_manager import QueueConfig
from core.services.base_service import BaseService

logger = logging.getLogger(__name__)


class BaseOutboundSender(BaseService, abc.ABC):
    """Base class for all outbound message senders."""
    
    def __init__(
        self,
        name: str,
        input_queue: str,
        error_queue: str,
        **kwargs
    ):
        """
        Initialize the outbound sender.
        
        Args:
            name: The name of the sender service
            input_queue: The name of the input queue to consume messages from
            error_queue: The name of the error queue for failed messages
            **kwargs: Additional keyword arguments for BaseService
        """
        super().__init__(name=name, **kwargs)
        self.input_queue_name = input_queue
        self.error_queue_name = error_queue
        
        # Will be initialized in on_start
        self.input_queue = None
        self.error_queue = None
    
    async def on_start(self) -> None:
        """Initialize the sender service."""
        # Initialize queues
        self.input_queue = await self.queue_manager.get_queue(self.input_queue_name)
        self.error_queue = await self.queue_manager.get_queue(self.error_queue_name)
        
        # Start the message processing loop
        self.create_task(self._process_messages())
    
    async def _process_messages(self) -> None:
        """Process messages from the input queue."""
        try:
            async for message_id, message in self.input_queue.consume():
                try:
                    # Process the message
                    success, error = await self.send_message(message)
                    
                    if success:
                        # Acknowledge the message on success
                        await self.input_queue.ack(message_id)
                        logger.debug(f"Successfully sent message {message.header.message_id}")
                    else:
                        # Forward to error queue on failure
                        message.header.metadata.setdefault("errors", []).append({
                            "service": self.name,
                            "error": error or "Unknown error"
                        })
                        await self.error_queue.publish(message)
                        await self.input_queue.ack(message_id)
                        
                except Exception as e:
                    logger.exception(f"Error processing message {message_id}: {e}")
                    # Forward to error queue and acknowledge to prevent blocking
                    if message:
                        message.header.metadata.setdefault("errors", []).append({
                            "service": self.name,
                            "error": f"Unexpected error: {str(e)}"
                        })
                        await self.error_queue.publish(message)
                    await self.input_queue.ack(message_id)
                    
        except asyncio.CancelledError:
            logger.info("Message processing cancelled")
            raise
        except Exception as e:
            logger.exception("Error in message processing loop")
            raise
    
    @abc.abstractmethod
    async def send_message(self, message: MessageEnvelope) -> tuple[bool, Optional[str]]:
        """
        Send a message to the destination.
        
        Args:
            message: The message to send
            
        Returns:
            A tuple of (success, error_message)
        """
        pass
    
    async def _handle_error(self, message: MessageEnvelope, error: str) -> None:
        """Handle an error that occurred during message processing."""
        logger.error(f"Error processing message {message.header.message_id}: {error}")
        
        # Add error to message metadata
        message.header.metadata.setdefault("errors", []).append({
            "service": self.name,
            "error": error
        })
        
        # Publish to error queue
        await self.error_queue.publish(message)
