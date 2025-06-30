"""Base interface for processing components."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from core.models.message import MessageEnvelope


class Processor(ABC):
    """Abstract base class for all processing components."""

    @abstractmethod
    async def start(self) -> None:
        """Start the processor."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the processor."""
        pass

    @abstractmethod
    async def process(self, message: MessageEnvelope) -> AsyncGenerator[MessageEnvelope, None]:
        """Process a message.
        
        Args:
            message: The message to process
            
        Yields:
            Processed message(s)
        """
        yield MessageEnvelope()  # For type checking

    @abstractmethod
    async def handle_error(self, error: Exception, message: Optional[MessageEnvelope] = None) -> None:
        """Handle processing errors.
        
        Args:
            error: The exception that occurred
            message: The message being processed when the error occurred (if any)
        """
        pass
