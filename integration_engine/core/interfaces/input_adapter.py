"""Base interface for input adapters."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from core.models.message import MessageEnvelope


class InputAdapter(ABC):
    """Abstract base class for all input adapters."""

    @abstractmethod
    async def start(self) -> None:
        """Start the input adapter."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the input adapter."""
        pass

    @abstractmethod
    async def receive(self) -> AsyncGenerator[MessageEnvelope, None]:
        """Receive messages from the input source.
        
        Yields:
            MessageEnvelope: Received message
        """
        yield MessageEnvelope()  # For type checking

    @abstractmethod
    async def acknowledge(self, message: MessageEnvelope) -> None:
        """Acknowledge successful processing of a message.
        
        Args:
            message: The message to acknowledge
        """
        pass

    @abstractmethod
    async def nacknowledge(self, message: MessageEnvelope, reason: str) -> None:
        """Negative acknowledgment for a failed message.
        
        Args:
            message: The message that failed
            reason: Reason for the failure
        """
        pass
