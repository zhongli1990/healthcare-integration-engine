"""Base interface for output adapters."""
from abc import ABC, abstractmethod
from typing import Optional

from core.models.message import MessageEnvelope


class OutputAdapter(ABC):
    """Abstract base class for all output adapters."""

    @abstractmethod
    async def start(self) -> None:
        """Start the output adapter."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the output adapter."""
        pass

    @abstractmethod
    async def send(self, message: MessageEnvelope) -> bool:
        """Send a message to the output destination.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        return False

    @abstractmethod
    async def batch_send(self, messages: list[MessageEnvelope]) -> dict:
        """Send multiple messages in a batch.
        
        Args:
            messages: List of messages to send
            
        Returns:
            dict: Results of the batch operation
        """
        return {"success": 0, "failed": len(messages), "errors": {}}
