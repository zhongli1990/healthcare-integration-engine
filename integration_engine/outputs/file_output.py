"""File-based output adapter."""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.interfaces.output_adapter import OutputAdapter
from core.models.message import MessageEnvelope, MessageHeader, MessageBody

logger = logging.getLogger(__name__)


class FileOutputAdapter(OutputAdapter):
    """Output adapter that writes messages to files."""

    def __init__(
        self,
        output_dir: str,
        file_extension: str = ".json",
        file_naming: str = "{message_id}",
        create_subdirs: bool = True,
        **kwargs
    ):
        """Initialize the file output adapter.
        
        Args:
            output_dir: Base directory for output files
            file_extension: File extension to use (e.g., ".json", ".hl7")
            file_naming: Template for generating filenames
                         Can include placeholders like {message_id}, {timestamp}, etc.
            create_subdirs: Whether to create subdirectories as needed
            **kwargs: Additional configuration options
        """
        self.output_dir = Path(output_dir)
        self.file_extension = file_extension
        self.file_naming = file_naming
        self.create_subdirs = create_subdirs
        self.config = kwargs
        
        # Create output directory if it doesn't exist
        if self.create_subdirs:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def start(self) -> None:
        """Start the output adapter."""
        logger.info(f"Started file output adapter writing to {self.output_dir}")
    
    async def stop(self) -> None:
        """Stop the output adapter."""
        logger.info("Stopped file output adapter")
    
    async def send(self, message: MessageEnvelope) -> bool:
        """Write a message to a file.
        
        Args:
            message: The message to write
            
        Returns:
            bool: True if the message was written successfully
        """
        try:
            # Generate output filename
            filename = self._generate_filename(message)
            output_path = self.output_dir / filename
            
            # Create parent directories if needed
            if self.create_subdirs:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Format message content based on content type
            content = self._format_message(message)
            
            # Write to file
            mode = self._get_file_mode(message)
            with open(output_path, mode) as f:
                f.write(content)
            
            logger.debug(f"Wrote message to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing message to file: {e}")
            return False
    
    async def batch_send(self, messages: list[MessageEnvelope]) -> dict:
        """Write multiple messages to files.
        
        Args:
            messages: List of messages to write
            
        Returns:
            dict: Results of the batch operation
        """
        results = {
            "success": 0,
            "failed": 0,
            "errors": {}
        }
        
        for i, message in enumerate(messages):
            try:
                success = await self.send(message)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"][i] = "Failed to write message"
            except Exception as e:
                results["failed"] += 1
                results["errors"][i] = str(e)
        
        return results
    
    def _generate_filename(self, message: MessageEnvelope) -> str:
        """Generate a filename for the output file.
        
        Args:
            message: The message to generate a filename for
            
        Returns:
            str: Generated filename with extension
        """
        # Get message metadata
        metadata = {
            "message_id": str(message.header.message_id),
            "timestamp": message.header.timestamp.isoformat(),
            "message_type": message.header.message_type,
            "source": message.header.source,
            "content_type": message.body.content_type.split(';')[0].split('/')[-1],
        }
        
        # Add any additional metadata
        metadata.update(message.header.metadata or {})
        metadata.update(message.body.metadata or {})
        
        try:
            # Format the filename using the template
            filename = self.file_naming.format(**metadata)
        except KeyError as e:
            logger.warning(f"Missing key in filename template: {e}, using message_id")
            filename = str(message.header.message_id)
        
        # Add file extension if not present
        if not filename.endswith(self.file_extension):
            filename += self.file_extension
            
        return filename
    
    def _format_message(self, message: MessageEnvelope) -> str:
        """Format the message content based on its type.
        
        Args:
            message: The message to format
            
        Returns:
            str: Formatted message content
        """
        content_type = message.body.content_type.lower()
        
        # Handle different content types
        if 'json' in content_type and message.body.content is not None:
            return json.dumps(message.body.content, indent=2)
        elif message.body.raw_content is not None:
            if isinstance(message.body.raw_content, bytes):
                return message.body.raw_content.decode('utf-8')
            return str(message.body.raw_content)
        elif message.body.content is not None:
            return str(message.body.content)
        else:
            return ""
    
    def _get_file_mode(self, message: MessageEnvelope) -> str:
        """Get the file mode for writing the message.
        
        Args:
            message: The message being written
            
        Returns:
            str: File mode ('w' for text, 'wb' for binary)
        """
        content_type = message.body.content_type.lower()
        if 'binary' in content_type or message.body.raw_content and isinstance(message.body.raw_content, bytes):
            return 'wb'
        return 'w'
